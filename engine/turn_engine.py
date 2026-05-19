"""
Motor de turno: implementa las 6 fases de un turno (B1–B6).

Fases en orden:
  1. Tirada de dados
  2. Asignación de dados a habilidades
  3. Caza de bestias / ciclado de mazos
  4. Combate (daño − defensa)
  5. Compra de objetos mágicos
  6. Fin del turno (tick de fichas de estado)
"""
from __future__ import annotations

import random
import sys
import os
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dice import DiceList
from dice_roller import roll_dice
from engine.models import (
    Team, StatusEffect, StatusToken, Item, ItemUsage, Beast, Ability
)


# ---------------------------------------------------------------------------
# Contexto de turno (estado acumulado durante las fases)
# ---------------------------------------------------------------------------

@dataclass
class TurnContext:
    attacker: Team
    defender: Team
    turn_number: int = 0
    dice: DiceList = field(default_factory=DiceList)
    total_damage: int = 0
    used_ability_names: set[str] = field(default_factory=set)
    # Fichas de estado aplicadas al defensor durante este turno
    statuses_applied: list[StatusToken] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Interfaz de política de jugador (plugable para IA / humano)
# ---------------------------------------------------------------------------

@runtime_checkable
class PlayerPolicy(Protocol):
    def assign_dice(self, ctx: TurnContext) -> list[tuple[str, int, list[int]]]:
        """
        Devuelve lista de (ability_name, hero_idx, dice_indices).
        hero_idx: índice del héroe en attacker.heroes.
        dice_indices: posiciones en ctx.dice a consumir.
        """
        ...

    def choose_hunt_beast(self, ctx: TurnContext) -> bool:
        """True si el jugador quiere cazar la bestia visible."""
        ...

    def choose_buy_item(self, ctx: TurnContext) -> bool:
        """True si el jugador quiere comprar el objeto visible."""
        ...

    def choose_use_item(self, ctx: TurnContext, item: Item, phase: str) -> bool:
        """True si el jugador quiere activar un objeto de su inventario en la fase dada."""
        ...

    def choose_apply_status(
        self, ctx: TurnContext
    ) -> list[tuple[StatusEffect, int]]:
        """
        Devuelve lista de (StatusEffect, turns) a aplicar al defensor.
        Generado por habilidades/objetos durante la fase de asignación.
        """
        ...


# ---------------------------------------------------------------------------
# Motor de turno
# ---------------------------------------------------------------------------

class TurnEngine:
    """Ejecuta las 6 fases de un turno y devuelve el TurnContext resultante."""

    def execute_turn(
        self,
        attacker: Team,
        defender: Team,
        policy: PlayerPolicy,
        turn_number: int = 0,
    ) -> TurnContext:
        ctx = TurnContext(
            attacker=attacker,
            defender=defender,
            turn_number=turn_number,
        )
        self._phase_roll(ctx)
        self._phase_assign(ctx, policy)
        self._phase_hunt_cycle(ctx, policy)
        self._phase_combat(ctx, policy)
        self._phase_buy(ctx, policy)
        self._phase_end(ctx)
        return ctx

    # ------------------------------------------------------------------
    # Fase 1 — Tirada de dados
    # ------------------------------------------------------------------

    def _phase_roll(self, ctx: TurnContext):
        # 4 dados verdes (regulares) + 1 dado rojo (especial)
        ctx.dice = roll_dice(number_of_dice=5, number_of_special_dice=1)

    # ------------------------------------------------------------------
    # Fase 2 — Asignación de dados a habilidades (B2)
    # ------------------------------------------------------------------

    def _phase_assign(self, ctx: TurnContext, policy: PlayerPolicy):
        # SILENCE bloquea todas las habilidades del turno
        if ctx.attacker.has_status(StatusEffect.SILENCE):
            return

        assignments = policy.assign_dice(ctx)

        for ability_name, hero_idx, dice_indices in assignments:
            if hero_idx >= len(ctx.attacker.heroes):
                continue
            hero = ctx.attacker.heroes[hero_idx]
            ability = next(
                (a for a in hero.abilities if a.name == ability_name), None
            )
            if ability is None:
                continue
            # No repetir la misma habilidad salvo que la carta lo permita
            if not ability.repeatable and ability_name in ctx.used_ability_names:
                continue

            ctx.used_ability_names.add(ability_name)
            ctx.total_damage += self._resolve_ability(ability, ctx, dice_indices)

        # Aplicar objetos activos durante la fase de asignación
        self._apply_active_items(ctx, policy, phase="assign")

        # Fichas de estado que el atacante quiere infligir
        for effect, turns in policy.choose_apply_status(ctx):
            token = StatusToken(effect=effect, turns_remaining=turns)
            ctx.defender.apply_status(token)
            ctx.statuses_applied.append(token)

    def _resolve_ability(
        self, ability: Ability, ctx: TurnContext, dice_indices: list[int]
    ) -> int:
        """
        Aplica el coste de dados y devuelve el daño generado.
        Los efectos complejos de carta se implementarán en Epic A/E;
        por ahora se usa el daño base de la habilidad más el valor de los dados.
        """
        consumed_values = []
        available = list(enumerate(ctx.dice))
        for idx in dice_indices:
            # Buscar la primera posición disponible que coincida con el índice pedido
            for pos, die in available:
                if pos == idx:
                    consumed_values.append(die.get_number())
                    available.remove((pos, die))
                    break

        # Daño = daño base + suma de caras (simplicación hasta Epic A)
        return ability.damage + sum(consumed_values)

    # ------------------------------------------------------------------
    # Fase 3 — Caza de bestias / ciclado de mazos (B6)
    # ------------------------------------------------------------------

    def _phase_hunt_cycle(self, ctx: TurnContext, policy: PlayerPolicy):
        # Revelar bestia si no hay ninguna visible
        if ctx.attacker.visible_beast is None and not ctx.attacker.beast_deck.is_empty():
            ctx.attacker.visible_beast = ctx.attacker.beast_deck.draw()

        if ctx.attacker.visible_beast and policy.choose_hunt_beast(ctx):
            self._attempt_hunt(ctx)
        else:
            # Ciclar el mazo de objetos si no se caza
            if not ctx.attacker.item_deck.is_empty():
                ctx.attacker.item_deck.cycle()

    def _attempt_hunt(self, ctx: TurnContext):
        beast = ctx.attacker.visible_beast
        if beast is None:
            return
        # La validación de dados la hace la política; aquí se aplica la recompensa
        ctx.attacker.diamonds += beast.reward_diamonds
        ctx.attacker.heal(beast.reward_hp)
        ctx.attacker.visible_beast = None
        # Revelar siguiente bestia
        if not ctx.attacker.beast_deck.is_empty():
            ctx.attacker.visible_beast = ctx.attacker.beast_deck.draw()

    # ------------------------------------------------------------------
    # Fase 4 — Combate: daño − defensa (B3 + B4)
    # ------------------------------------------------------------------

    def _phase_combat(self, ctx: TurnContext, policy: PlayerPolicy):
        if ctx.total_damage == 0:
            return

        # Daño extra de fichas de estado activas en el defensor
        bonus = self._compute_status_damage(ctx.defender)

        total = ctx.total_damage + bonus

        # Aplicar objetos activos durante el combate
        self._apply_active_items(ctx, policy, phase="combat")

        # Fase de defensa: 1 dado por escudo (máx 3); 4/5/6 bloquea 1 daño
        defended = self._roll_defense(ctx.defender)

        # FREEZE: el defensor congela → no puede tirar dados de defensa
        if ctx.defender.has_status(StatusEffect.FREEZE):
            defended = 0

        net = max(0, total - defended)
        ctx.defender.take_damage(net)

    def _compute_status_damage(self, team: Team) -> int:
        extra = 0
        for s in team.active_statuses:
            if s.effect == StatusEffect.POISON:
                extra += 1
            elif s.effect == StatusEffect.BURN:
                extra += 2
            elif s.effect == StatusEffect.BLEEDING:
                extra += 1
        return extra

    def _roll_defense(self, defender: Team) -> int:
        """1 dado por escudo (máx 3). Cada 4/5/6 bloquea 1 daño."""
        num_dice = min(defender.shields, 3)
        return sum(1 for _ in range(num_dice) if random.randint(1, 6) >= 4)

    # ------------------------------------------------------------------
    # Fase 5 — Compra y uso de objetos (B5)
    # ------------------------------------------------------------------

    def _phase_buy(self, ctx: TurnContext, policy: PlayerPolicy):
        # Revelar objeto si no hay ninguno visible
        if ctx.attacker.visible_item is None and not ctx.attacker.item_deck.is_empty():
            ctx.attacker.visible_item = ctx.attacker.item_deck.draw()

        if ctx.attacker.visible_item:
            item = ctx.attacker.visible_item
            if (
                policy.choose_buy_item(ctx)
                and ctx.attacker.diamonds >= item.cost_diamonds
            ):
                ctx.attacker.diamonds -= item.cost_diamonds
                ctx.attacker.items_owned.append(item)
                ctx.attacker.visible_item = None
                # Revelar siguiente objeto
                if not ctx.attacker.item_deck.is_empty():
                    ctx.attacker.visible_item = ctx.attacker.item_deck.draw()

        # Activar objetos durante la fase de compra
        self._apply_active_items(ctx, policy, phase="buy")

    def _apply_active_items(self, ctx: TurnContext, policy: PlayerPolicy, phase: str):
        """Permite usar objetos del inventario en las fases válidas (assign/combat/buy)."""
        for item in list(ctx.attacker.items_owned):
            if item.usage == ItemUsage.PERMANENT:
                # Los permanentes aplican su bono automáticamente en combate
                if phase == "combat":
                    ctx.total_damage += item.damage_bonus
                continue

            if not policy.choose_use_item(ctx, item, phase):
                continue

            # Usar el objeto
            ctx.total_damage += item.damage_bonus
            if item.usage == ItemUsage.SINGLE_USE:
                ctx.attacker.items_owned.remove(item)
            elif item.usage == ItemUsage.MULTI_USE:
                item.uses_remaining -= 1
                if item.uses_remaining <= 0:
                    ctx.attacker.items_owned.remove(item)

    # ------------------------------------------------------------------
    # Fase 6 — Fin del turno: tick de fichas de estado
    # ------------------------------------------------------------------

    def _phase_end(self, ctx: TurnContext):
        # Las fichas de estado en el defensor se decrementan al final del turno
        # del atacante (es decir: al final del turno del equipo que las aplicó).
        ctx.defender.tick_statuses()
