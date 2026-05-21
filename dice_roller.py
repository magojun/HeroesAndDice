"""
dice_roller.py — API de compatibilidad (F4).

Las funciones de este módulo siguen disponibles para no romper código existente.
En código nuevo, usar heroesydados.dice.model.DiceRoll directamente:

    from heroesydados.dice.model import DiceRoll
    roll = DiceRoll.roll(seed=42)   # 4 verdes + 1 rojo, reproducible

Mapa de equivalencias (legacy → nuevo):
  roll_dice(5, 1)  →  DiceRoll.roll()
  has_combination  →  (sin equivalente directo; lógica de GreedyPolicy en ai/)
"""
from __future__ import annotations

from copy import copy
from dice import DiceList, RegularDice, SpecialDice


def roll_one_die(is_special_dice: bool = False):
    return SpecialDice() if is_special_dice else RegularDice()


def roll_dice(number_of_dice: int = 5, number_of_special_dice: int = 1) -> DiceList:
    """
    Lanza number_of_dice dados, de los cuales number_of_special_dice son rojos.
    Devuelve DiceList (API heredada). En código nuevo preferir DiceRoll.roll().
    """
    dice_roll = DiceList()
    regular_count = number_of_dice - number_of_special_dice
    for _ in range(regular_count):
        dice_roll.append(roll_one_die())
    for _ in range(number_of_special_dice):
        dice_roll.append(roll_one_die(True))
    return dice_roll


def find_combination(dice_roll: DiceList, dice_combination: list) -> list:
    dice_roll = copy(dice_roll)
    combination_found = []
    for combination in dice_combination:
        for die in dice_roll:
            if combination == die:
                dice_roll.remove(die)
                combination_found.append(die)
                break
    return combination_found if combination_found == dice_combination else []


def has_combination(dice_roll: DiceList, dice_combination: list) -> bool:
    return find_combination(dice_roll, dice_combination) == dice_combination


def has_at_least_one_combination(dice_roll, dice_combinations) -> bool:
    return any(has_combination(dice_roll, c) for c in dice_combinations)


def found_combinations(dice_roll, dice_combinations) -> list:
    combinations_found = []
    for combination in dice_combinations:
        result = find_combination(dice_roll, combination)
        if isinstance(result, list) and result:
            combinations_found.append(result)
    return combinations_found


def has_all_combinations(dice_roll, dice_combinations) -> bool:
    dice_roll = copy(dice_roll)
    any_problem = False
    for combination in dice_combinations:
        if any(isinstance(s, list) for s in combination):
            if not has_at_least_one_combination(dice_roll, combination):
                any_problem = True
            result_found = found_combinations(dice_roll, combination)
            one_removed = False
            for one_result in result_found:
                if not one_removed and isinstance(one_result, list) and one_result:
                    for result in one_result:
                        for die in dice_roll:
                            if result == die:
                                dice_roll.remove(die)
                                one_removed = True
                                break
        else:
            result_found = find_combination(dice_roll, combination)
            if not has_combination(dice_roll, combination):
                any_problem = True
            if isinstance(result_found, list) and result_found:
                for result in result_found:
                    for die in dice_roll:
                        if result == die:
                            dice_roll.remove(die)
                            break
    return not any_problem


# ---------------------------------------------------------------------------
# Combinaciones predefinidas (legacy — usadas en dice_roller original)
# ---------------------------------------------------------------------------

def get_pairs_combination() -> list:
    return [[v, v] for v in range(1, 7)]


def get_smallers_combination() -> list:
    return [[1], [2], [3]]


def get_pairs_combination_plus_another_combination(second_dice_combination) -> list:
    return [second_dice_combination, get_pairs_combination()]
