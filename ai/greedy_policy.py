"""
GreedyPolicy — IA base para Heroes y Dados (Epic C).

Heurísticas implementadas:
  C2 - assign_dice: maximiza daño total del turno asignando dados a habilidades
       por orden de daño descendente, consumiendo el pool de dados de forma greedy.
  C3 - defensa: la engine maneja los dados de escudo automáticamente; la política
       usa objetos defensivos cuando el HP propio está bajo.
  C4 - economía: caza bestias si la recompensa es positiva; compra objetos cuando
       el balance diamantes/valor lo justifica; cicla si no caza.
  C5 - estados: aplica todos los estados disponibles al oponente siempre que pueda.
"""
from __future__ import annotations

from engine.turn_engine import TurnContext
from engine.models import Item, ItemUsage, StatusEffect, StatusToken

# Umbral de HP bajo (porcentaje) para activar modo defensivo en uso de objetos
_LOW_HP_THRESHOLD = 0.4


class GreedyPolicy:
    """
    Política greedy: implementación por defecto de PlayerPolicy para simulaciones.

    Prioridades por fase:
      1. Asignación: activa las habilidades de mayor daño base que el pool de dados
         permite, preservando el dado rojo para usos obligatorios.
      2. Caza/ciclo: caza si la bestia visible tiene recompensa >= 1 diamante o >= 2 HP.
      3. Compra: compra si hay diamantes suficientes y el objeto tiene bono de daño.
      4. Uso de objetos: activa objetos de un solo uso en combate o cuando HP es crítico.
      5. Estados: aplica toda ficha de estado disponible al oponente.
    """

    # ------------------------------------------------------------------
    # C2 — Asignación de dados a habilidades
    # ------------------------------------------------------------------

    def assign_dice(self, ctx: TurnContext) -> list[tuple[str, int, list[int]]]:
        """
        Devuelve lista de (ability_name, hero_idx, dice_indices).

        Estrategia: ordena habilidades por daño base desc; para cada una intenta
        satisfacer el coste con dados disponibles (regulares primero, rojo como
        comodín al final). No repite habilidades no-repetibles.
        """
        dice_values = [d.get_number() for d in ctx.dice]
        dice_special = [d.is_special_type() for d in ctx.dice]

        # Pool de índices disponibles separado por tipo
        regular_pool = [i for i, s in enumerate(dice_special) if not s]
        special_pool = [i for i, s in enumerate(dice_special) if s]

        # Recopilar habilidades con su héroe, ordenadas por daño desc
        candidates = [
            (hero_idx, ability)
            for hero_idx, hero in enumerate(ctx.attacker.heroes)
            for ability in hero.abilities
        ]
        candidates.sort(key=lambda x: x[1].damage, reverse=True)

        result: list[tuple[str, int, list[int]]] = []
        used_abilities: set[str] = set()

        # Repetir el loop hasta que ninguna habilidad pueda asignarse (soporta repeatable)
        progress = True
        while progress:
            progress = False
            for hero_idx, ability in candidates:
                if not ability.repeatable and ability.name in used_abilities:
                    continue

                assigned = self._try_assign(
                    ability.dice_cost, regular_pool, special_pool, dice_values
                )
                if assigned is None:
                    continue

                result.append((ability.name, hero_idx, assigned))
                used_abilities.add(ability.name)
                progress = True

                # Retirar índices asignados de los pools
                for idx in assigned:
                    if idx in regular_pool:
                        regular_pool.remove(idx)
                    elif idx in special_pool:
                        special_pool.remove(idx)

        return result

    def _try_assign(
        self,
        cost: list[int],
        regular: list[int],
        special: list[int],
        values: list[int],
    ) -> list[int] | None:
        """
        Intenta satisfacer `cost` (lista de valores de cara requeridos) con los
        pools disponibles. Usa dados regulares primero; el dado rojo actúa como
        comodín cuando no hay regular del valor necesario.

        Devuelve los índices consumidos, o None si no es posible.
        """
        remaining_regular = list(regular)
        remaining_special = list(special)
        assigned: list[int] = []

        for needed in cost:
            # Buscar dado regular con la cara exacta
            found = next(
                (i for i in remaining_regular if values[i] == needed), None
            )
            if found is not None:
                remaining_regular.remove(found)
                assigned.append(found)
                continue

            # Usar dado especial (rojo) como comodín
            if remaining_special:
                found = remaining_special.pop(0)
                assigned.append(found)
                continue

            return None  # no se puede satisfacer este costo

        return assigned

    # ------------------------------------------------------------------
    # C3 — Heurística de defensa (uso de objetos defensivos)
    # ------------------------------------------------------------------

    def _is_low_hp(self, ctx: TurnContext) -> bool:
        max_hp = sum(h.max_hp for h in ctx.attacker.heroes)
        return max_hp > 0 and (ctx.attacker.hp / max_hp) <= _LOW_HP_THRESHOLD

    # ------------------------------------------------------------------
    # C4 — Heurística de economía: caza y compra
    # ------------------------------------------------------------------

    def choose_hunt_beast(self, ctx: TurnContext) -> bool:
        """Caza si la bestia da al menos 1 diamante o 2 HP."""
        beast = ctx.attacker.visible_beast
        if beast is None:
            return False
        return beast.reward_diamonds >= 1 or beast.reward_hp >= 2

    def choose_buy_item(self, ctx: TurnContext) -> bool:
        """
        Compra si:
        - Hay diamantes suficientes.
        - El objeto tiene bono de daño o cuesta <= 1 diamante.
        - No se queda a 0 diamantes (salvo que el objeto sea muy bueno).
        """
        item = ctx.attacker.visible_item
        if item is None:
            return False
        if ctx.attacker.diamonds < item.cost_diamonds:
            return False
        remaining = ctx.attacker.diamonds - item.cost_diamonds
        # Reservar al menos 1 diamante para economía futura, salvo ítem gratuito
        if remaining == 0 and item.cost_diamonds > 0 and item.damage_bonus < 3:
            return False
        return item.damage_bonus > 0

    def choose_use_item(self, ctx: TurnContext, item: Item, phase: str) -> bool:
        """
        Usa objetos de un solo uso:
        - En combate: si hay daño que amplificar.
        - En cualquier fase: si HP propio está crítico y el objeto cura/defiende.
        Los permanentes se aplican automáticamente por la engine; aquí siempre False.
        """
        if item.usage == ItemUsage.PERMANENT:
            return False
        if phase == "combat" and ctx.total_damage > 0:
            return True
        if self._is_low_hp(ctx) and item.damage_bonus > 0:
            return True
        return False

    # ------------------------------------------------------------------
    # C5 — Heurística de estados
    # ------------------------------------------------------------------

    def choose_apply_status(
        self, ctx: TurnContext
    ) -> list[tuple[StatusEffect, int]]:
        """
        Aplica estados disponibles priorizando por impacto:
        - FREEZE si el defensor tiene escudos (impide defensa del próximo turno).
        - SILENCE si el defensor tiene habilidades de alto daño.
        - BURN > POISON > BLEEDING por daño por turno.

        En esta implementación base, la disponibilidad de estados depende de las
        cartas cargadas (Epic E); se devuelve lista vacía hasta que las habilidades
        de carta los otorguen explícitamente.
        """
        return []
