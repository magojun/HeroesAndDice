from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Die:
    value: int
    is_red: bool = False

    def __post_init__(self) -> None:
        if not (1 <= self.value <= 6):
            raise ValueError(f"Die value must be 1-6, got {self.value}")


class DiceRoll:
    """Single roll of 4 green dice + 1 red die per turn.

    Dice are NOT re-rolled unless a skill/object explicitly allows it.
    Pass a seed for reproducible rolls (useful for tests and simulations).
    """

    GREEN_COUNT = 4
    RED_COUNT = 1

    def __init__(self, seed: Optional[int] = None) -> None:
        rng = random.Random(seed)
        self._dice: list[Die] = [
            Die(rng.randint(1, 6), is_red=False) for _ in range(self.GREEN_COUNT)
        ] + [Die(rng.randint(1, 6), is_red=True)]

    @classmethod
    def roll(cls, seed: Optional[int] = None) -> "DiceRoll":
        return cls(seed)

    @classmethod
    def from_values(cls, green: list[int], red: int) -> "DiceRoll":
        """Build a DiceRoll from explicit values (for tests/replays)."""
        if len(green) != cls.GREEN_COUNT:
            raise ValueError(f"Expected {cls.GREEN_COUNT} green dice, got {len(green)}")
        instance = object.__new__(cls)
        instance._dice = [Die(v, is_red=False) for v in green] + [Die(red, is_red=True)]
        return instance

    @property
    def dice(self) -> list[Die]:
        return list(self._dice)

    def green_dice(self) -> list[Die]:
        return [d for d in self._dice if not d.is_red]

    def red_die(self) -> Die:
        return next(d for d in self._dice if d.is_red)

    def all_values(self) -> list[int]:
        return [d.value for d in self._dice]

    def green_values(self) -> list[int]:
        return [d.value for d in self.green_dice()]

    def red_value(self) -> int:
        return self.red_die().value

    def __repr__(self) -> str:
        greens = self.green_values()
        return f"DiceRoll(green={greens}, red={self.red_value()})"
