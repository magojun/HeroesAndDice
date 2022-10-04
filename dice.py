import abc
import random


class Dice(metaclass=abc.ABCMeta):
    # The number of the dice
    die_number = abc.abstractproperty()

    @abc.abstractmethod
    def roll(self):
        """Roll the dice number"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_number(self):
        """Return the dice number"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_type(self):
        """Get the type of dice"""
        raise NotImplementedError


class RegularDice(Dice):
    """Regular six faced dice."""
    die_number = 0

    def roll(self) -> int:
        return random.randint(1, 6)

    def get_number(self) -> int:
        return self.die_number

    def is_special_type(self):
        return False


class SpecialDice(Dice):
    """Regular six faced dice."""
    die_number = 0

    def roll(self) -> int:
        return random.randint(1, 6)

    def get_number(self) -> int:
        return self.die_number

    def is_special_type(self):
        return True
