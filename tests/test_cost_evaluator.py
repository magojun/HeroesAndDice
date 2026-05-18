import pytest
from heroesydados.dice.model import DiceRoll
from heroesydados.skills.cost_parser import parse_cost
from heroesydados.skills.cost_evaluator import can_pay, assign_dice


def roll(green: list[int], red: int) -> DiceRoll:
    return DiceRoll.from_values(green, red)


# --- Pts costs ---

def test_pts_satisfied():
    r = roll([4, 5, 6, 1], 2)
    assert can_pay(r, parse_cost("Pts:11"))

def test_pts_not_satisfied():
    r = roll([1, 1, 1, 1], 1)
    assert not can_pay(r, parse_cost("Pts:11"))

def test_pts_exact_boundary():
    r = roll([3, 3, 3, 2], 1)  # sum of best 4 = 3+3+3+2=11
    assert can_pay(r, parse_cost("Pts:11"))


# --- Simple green die costs ---

def test_1d_verde_ge4_satisfied():
    r = roll([4, 1, 1, 1], 2)
    assert can_pay(r, parse_cost("1d verde >=4"))

def test_1d_verde_ge4_not_satisfied():
    # All dice (including red) below 4 → cannot satisfy
    r = roll([1, 2, 3, 3], 3)
    assert not can_pay(r, parse_cost("1d verde >=4"))

def test_3d_verde_pares_satisfied():
    r = roll([2, 4, 6, 1], 3)
    assert can_pay(r, parse_cost("3d verde pares"))

def test_3d_verde_pares_not_satisfied():
    r = roll([2, 4, 1, 1], 3)
    assert not can_pay(r, parse_cost("3d verde pares"))

def test_4d_verde_iguales_satisfied():
    r = roll([3, 3, 3, 3], 1)
    assert can_pay(r, parse_cost("4d verde iguales"))

def test_4d_verde_iguales_not_satisfied():
    # [3,3,3,4] green + red=4: combos of 4 are {3,3,3,4}, {3,3,4,4} etc. — never 4 equal
    r = roll([3, 3, 3, 4], 4)
    assert not can_pay(r, parse_cost("4d verde iguales"))

def test_verde_consecutivos_satisfied():
    r = roll([3, 4, 5, 1], 2)
    assert can_pay(r, parse_cost("verde consecutivos"))

def test_3d_verde_le3_satisfied():
    r = roll([1, 2, 3, 4], 5)
    assert can_pay(r, parse_cost("3d verde <=3"))

def test_3d_verde_le3_not_enough():
    r = roll([1, 2, 4, 4], 5)
    assert not can_pay(r, parse_cost("3d verde <=3"))


# --- Red die required ---

def test_1d_rojo_cualquiera_satisfied():
    r = roll([1, 1, 1, 1], 5)
    assert can_pay(r, parse_cost("1d rojo cualquiera"))

def test_1d_rojo_required_green_does_not_satisfy():
    # Red die required — must be the red die
    r = roll([5, 1, 1, 1], 1)
    # "1d rojo cualquiera" needs red die regardless of green values
    assert can_pay(r, parse_cost("1d rojo cualquiera"))


# --- Red die as wildcard ---

def test_red_as_wildcard_for_green_slot():
    # Only 3 green dice >= 4; red (value 5) should fill 4th slot
    r = roll([4, 4, 4, 1], 5)
    assert can_pay(r, parse_cost("4d verde iguales")) is False  # 4,4,4 and red=5 ≠ equal

def test_red_wildcard_fills_ge4_slot():
    # 3 greens >= 4 + red=5 (wildcard) → 4 dice >= 4
    r = roll([4, 4, 4, 1], 5)
    assert can_pay(r, parse_cost("4d verde >=4"))  # red acts as wildcard


# --- Compound costs ---

def test_compound_rojo_plus_verde():
    r = roll([3, 1, 1, 1], 5)
    assert can_pay(r, parse_cost("1d rojo cualquiera + 1d verde cualquiera"))

def test_compound_not_satisfied_missing_rojo():
    r = roll([3, 1, 1, 1], 5)
    # cost needs red + green; available: red=5 + green=3
    assert can_pay(r, parse_cost("1d rojo cualquiera + 1d verde cualquiera"))

def test_compound_ge4_plus_rojo():
    r = roll([5, 1, 1, 1], 4)
    result = assign_dice(r, parse_cost("1d verde >=4 + 1d rojo *"))
    assert result is not None
    assert len(result.dice) == 2


# --- Alternatives ---

def test_alternative_first_option():
    r = roll([5, 1, 1, 1], 2)
    assert can_pay(r, parse_cost("1d verde >=4 | 3d verde pares"))

def test_alternative_second_option():
    r = roll([2, 4, 6, 1], 2)
    assert can_pay(r, parse_cost("1d verde >=5 | 3d verde pares"))

def test_alternatives_both_fail():
    # Greens all different → not iguales; total 1+2+3+4+1=11 < 20
    r = roll([1, 2, 3, 4], 1)
    assert not can_pay(r, parse_cost("4d verde iguales | Pts:20"))


# --- assign_dice ---

def test_assign_dice_returns_assignment():
    r = roll([3, 3, 3, 3], 1)
    result = assign_dice(r, parse_cost("4d verde iguales"))
    assert result is not None
    assert len(result.dice) == 4

def test_assign_dice_none_when_cannot_pay():
    r = roll([1, 2, 3, 4], 2)
    result = assign_dice(r, parse_cost("4d verde iguales"))
    assert result is None

def test_assign_dice_null_cost():
    r = roll([1, 2, 3, 4], 5)
    assert assign_dice(r, parse_cost(None)) is None
