"""
dice.py — API de compatibilidad (F4).

El modelo canónico de dados vive en heroesydados/dice/model.py (Die, DiceRoll).
Este módulo mantiene las clases heredadas (RegularDice, SpecialDice, DiceList)
para no romper el código existente del engine. Nuevo código debe importar
directamente de heroesydados.dice.model.

Mapa de equivalencias:
  RegularDice  →  Die(value, is_red=False)
  SpecialDice  →  Die(value, is_red=True)
  DiceList     →  list[Die]   (usar DiceRoll.dice en código nuevo)
"""
import abc
import random
import warnings

# Re-exportar la API nueva para que import * la incluya
from heroesydados.dice.model import Die, DiceRoll  # noqa: F401

__all__ = [
    "Dice", "RegularDice", "SpecialDice", "DiceList",
    "Die", "DiceRoll",        # API nueva accesible desde aquí
]


class Dice(metaclass=abc.ABCMeta):
    """Clase base heredada. Preferir heroesydados.dice.model.Die en código nuevo."""

    die_number: int = 0

    def __init__(self):
        self.die_number = self.roll()

    @abc.abstractmethod
    def roll(self) -> int: ...

    @abc.abstractmethod
    def get_number(self) -> int: ...

    @abc.abstractmethod
    def is_special_type(self) -> bool: ...

    def to_die(self) -> Die:
        """Convierte al nuevo tipo Die."""
        return Die(value=self.die_number, is_red=self.is_special_type())


class RegularDice(Dice):
    """Dado verde (regular). Equivale a Die(value, is_red=False)."""

    die_number = 0

    def roll(self) -> int:
        return random.randint(1, 6)

    def get_number(self) -> int:
        return self.die_number

    def is_special_type(self) -> bool:
        return False


class SpecialDice(Dice):
    """Dado rojo (especial / comodín). Equivale a Die(value, is_red=True)."""

    die_number = 0

    def roll(self) -> int:
        return random.randint(1, 6)

    def get_number(self) -> int:
        return self.die_number

    def is_special_type(self) -> bool:
        return True


class DiceList(list):
    """Lista de dados heredada. En código nuevo usar list[Die] o DiceRoll.dice."""

    def has_special_dice(self) -> bool:
        return any(d.is_special_type() for d in self)

    def to_dice_roll_values(self) -> DiceRoll:
        """Convierte a DiceRoll del modelo nuevo (requiere exactamente 4 verdes + 1 rojo)."""
        greens = [d.get_number() for d in self if not d.is_special_type()]
        reds   = [d.get_number() for d in self if d.is_special_type()]
        if len(reds) != 1:
            raise ValueError(f"DiceList debe tener exactamente 1 dado rojo; tiene {len(reds)}")
        return DiceRoll.from_values(greens, reds[0])
