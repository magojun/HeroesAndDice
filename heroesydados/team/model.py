from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from heroesydados.cards.models import Hero

MAX_SHIELDS = 3


@dataclass
class HeroState:
    hero: "Hero"
    frozen: bool = False


@dataclass
class Team:
    """Game state for one player's team of 2 heroes.

    life   — single shared life tracker; starts at sum of both heroes' vida.
    shields — active shields = sum of non-frozen heroes' escudo, capped at MAX_SHIELDS.
              A frozen hero does not contribute shields (Congelar state).
    """

    heroes: list[HeroState]
    _life: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.heroes) != 2:
            raise ValueError("A team must have exactly 2 heroes")
        self._life = sum(hs.hero.vida for hs in self.heroes)

    @classmethod
    def from_heroes(cls, hero_a: "Hero", hero_b: "Hero") -> "Team":
        return cls(heroes=[HeroState(hero_a), HeroState(hero_b)])

    @property
    def life(self) -> int:
        return self._life

    def take_damage(self, damage: int) -> int:
        """Apply damage; returns actual damage taken (life cannot go below 0)."""
        actual = min(damage, self._life)
        self._life = max(0, self._life - damage)
        return actual

    def heal(self, amount: int) -> int:
        """Restore life; returns amount actually healed."""
        self._life += amount
        return amount

    @property
    def shields(self) -> int:
        active = sum(hs.hero.escudo for hs in self.heroes if not hs.frozen)
        return min(active, MAX_SHIELDS)

    @property
    def is_defeated(self) -> bool:
        return self._life <= 0

    def freeze_hero(self, index: int) -> None:
        """Freeze hero at index; frozen heroes don't contribute shields."""
        self.heroes[index].frozen = True

    def unfreeze_all(self) -> None:
        for hs in self.heroes:
            hs.frozen = False

    def __repr__(self) -> str:
        names = [hs.hero.nombre for hs in self.heroes]
        return f"Team({names}, life={self._life}, shields={self.shields})"
