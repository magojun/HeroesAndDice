import pytest
from heroesydados.dice.model import Die, DiceRoll


def test_die_valid_values():
    for v in range(1, 7):
        d = Die(v)
        assert d.value == v


def test_die_invalid_value():
    with pytest.raises(ValueError):
        Die(0)
    with pytest.raises(ValueError):
        Die(7)


def test_dice_roll_has_4_green_1_red():
    roll = DiceRoll.roll()
    assert len(roll.green_dice()) == 4
    assert roll.red_die().is_red is True
    assert all(not d.is_red for d in roll.green_dice())


def test_dice_roll_values_in_range():
    for _ in range(50):
        roll = DiceRoll.roll()
        assert all(1 <= v <= 6 for v in roll.all_values())


def test_dice_roll_reproducible_with_seed():
    r1 = DiceRoll.roll(seed=42)
    r2 = DiceRoll.roll(seed=42)
    assert r1.all_values() == r2.all_values()


def test_dice_roll_different_seeds_differ():
    r1 = DiceRoll.roll(seed=1)
    r2 = DiceRoll.roll(seed=2)
    assert r1.all_values() != r2.all_values()


def test_dice_roll_from_values():
    roll = DiceRoll.from_values([1, 2, 3, 4], 5)
    assert roll.green_values() == [1, 2, 3, 4]
    assert roll.red_value() == 5


def test_dice_roll_from_values_wrong_count():
    with pytest.raises(ValueError):
        DiceRoll.from_values([1, 2, 3], 4)


def test_dice_roll_repr():
    roll = DiceRoll.from_values([1, 2, 3, 4], 6)
    assert "green" in repr(roll)
    assert "red" in repr(roll)


def test_dice_roll_total_dice_count():
    roll = DiceRoll.roll(seed=0)
    assert len(roll.dice) == 5
