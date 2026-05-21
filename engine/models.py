from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StatusEffect(Enum):
    POISON = "poison"
    BURN = "burn"
    FREEZE = "freeze"
    BLEEDING = "bleeding"
    SILENCE = "silence"


class ItemUsage(Enum):
    PERMANENT = "permanent"
    SINGLE_USE = "single_use"
    MULTI_USE = "multi_use"


@dataclass
class StatusToken:
    effect: StatusEffect
    # Duración: se decrementa al final del turno del oponente; expira cuando llega a 0.
    turns_remaining: int = 1


@dataclass
class Ability:
    name: str
    dice_cost: list[int]        # valores de cara requeridos para activar
    damage: int = 0             # daño base (efectos complejos: Epic A/E)
    repeatable: bool = False    # si puede usarse más de una vez por turno


@dataclass
class Hero:
    name: str
    max_hp: int
    shields: int = 0            # fichas de escudo que aporta al equipo (acumuladas, máx 3)
    abilities: list[Ability] = field(default_factory=list)


@dataclass
class Item:
    name: str
    cost_diamonds: int
    usage: ItemUsage
    uses_remaining: int = 1     # relevante para MULTI_USE
    damage_bonus: int = 0       # bono aplicado al combate cuando se activa


@dataclass
class Beast:
    name: str
    dice_cost: list[int]        # dados necesarios para cazar la bestia
    reward_diamonds: int = 0
    reward_hp: int = 0


@dataclass
class Deck:
    cards: list = field(default_factory=list)

    def draw(self):
        return self.cards.pop(0) if self.cards else None

    def cycle(self):
        """Mueve la carta visible al fondo del mazo."""
        if self.cards:
            self.cards.append(self.cards.pop(0))

    def is_empty(self) -> bool:
        return len(self.cards) == 0


@dataclass
class Team:
    heroes: list[Hero]
    diamonds: int = 0
    item_deck: Deck = field(default_factory=Deck)
    beast_deck: Deck = field(default_factory=Deck)
    visible_item: Optional[Item] = None
    visible_beast: Optional[Beast] = None
    active_statuses: list[StatusToken] = field(default_factory=list)
    items_owned: list[Item] = field(default_factory=list)

    # HP y escudos se calculan de los héroes al crear el equipo.
    _hp: int = field(init=False, repr=False)
    _shields: int = field(init=False, repr=False)

    def __post_init__(self):
        self._hp = sum(h.max_hp for h in self.heroes)
        raw_shields = sum(h.shields for h in self.heroes)
        self._shields = min(raw_shields, 3)

    @property
    def hp(self) -> int:
        return self._hp

    @property
    def shields(self) -> int:
        return self._shields

    def is_defeated(self) -> bool:
        return self._hp <= 0

    def take_damage(self, amount: int):
        self._hp = max(0, self._hp - amount)

    def heal(self, amount: int):
        self._hp += amount

    def has_status(self, effect: StatusEffect) -> bool:
        return any(s.effect == effect for s in self.active_statuses)

    def apply_status(self, token: StatusToken):
        self.active_statuses.append(token)

    def tick_statuses(self) -> list[StatusToken]:
        """Decrementa duración de fichas de estado; devuelve las expiradas."""
        expired, remaining = [], []
        for s in self.active_statuses:
            s.turns_remaining -= 1
            (expired if s.turns_remaining <= 0 else remaining).append(s)
        self.active_statuses = remaining
        return expired
