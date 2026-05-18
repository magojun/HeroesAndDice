"""Evaluador de costos: dada una tirada y un costo parseado, determina si la
tirada satisface el costo y qué subconjunto de dados se consume.

Regla del dado rojo (reglamento sección 4, fase 2):
  - Si una habilidad requiere dado rojo, SE DEBE usar el dado rojo para ese slot.
  - Si una habilidad NO requiere dado rojo, el dado rojo puede actuar como comodín
    (asignarse a cualquier slot de color 'verde' o 'cualquiera').
  - El dado rojo es único: sólo puede satisfacer UN slot.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Optional

from heroesydados.dice.model import Die, DiceRoll
from heroesydados.skills.cost_parser import (
    CostGroup, CostOption, ParsedCost,
    COLOR_VERDE, COLOR_ROJO, COLOR_ANY,
    CONSTRAINT_PARES, CONSTRAINT_IMPARES, CONSTRAINT_IGUALES, CONSTRAINT_CONSECUTIVOS,
)


# ---------------------------------------------------------------------------
# Assignment result
# ---------------------------------------------------------------------------

@dataclass
class Assignment:
    """Dice consumed to pay a cost option."""
    dice: list[Die]           # dice used, in order matching the cost groups
    option_index: int = 0     # which alternative (|) was satisfied


# ---------------------------------------------------------------------------
# Constraint helpers
# ---------------------------------------------------------------------------

def _satisfies_value(die: Die, group: CostGroup) -> bool:
    if group.min_value is not None and die.value < group.min_value:
        return False
    if group.max_value is not None and die.value > group.max_value:
        return False
    return True


def _satisfies_color(die: Die, group: CostGroup) -> bool:
    if group.color == COLOR_ROJO:
        return die.is_red
    if group.color == COLOR_VERDE:
        return not die.is_red  # red die may act as wildcard in caller
    return True  # COLOR_ANY: any die


def _satisfies_constraint_group(values: list[int], constraint: Optional[str]) -> bool:
    if constraint is None:
        return True
    if constraint == CONSTRAINT_PARES:
        return all(v % 2 == 0 for v in values)
    if constraint == CONSTRAINT_IMPARES:
        return all(v % 2 == 1 for v in values)
    if constraint == CONSTRAINT_IGUALES:
        return len(set(values)) == 1
    if constraint == CONSTRAINT_CONSECUTIVOS:
        s = sorted(values)
        return all(s[i + 1] - s[i] == 1 for i in range(len(s) - 1))
    return True


# ---------------------------------------------------------------------------
# Pts group satisfaction
# ---------------------------------------------------------------------------

def _try_pts(available: list[Die], group: CostGroup) -> Optional[list[Die]]:
    """Try to satisfy a Pts:N group using any subset of available dice.

    Returns the minimal subset (fewest dice) whose sum >= pts_value, or None.
    Prefers green dice; uses red only if necessary (it's a wildcard here).
    """
    target = group.pts_value or 0

    # Sort so green dice come first (preserve red die for explicit-red slots)
    sorted_dice = sorted(available, key=lambda d: (d.is_red, -d.value))

    # Greedy: take highest-value dice until sum is reached
    chosen: list[Die] = []
    total = 0
    for die in sorted_dice:
        if total >= target:
            break
        chosen.append(die)
        total += die.value

    return chosen if total >= target else None


# ---------------------------------------------------------------------------
# Single CostGroup satisfaction
# ---------------------------------------------------------------------------

def _try_group(available: list[Die], group: CostGroup) -> Optional[list[Die]]:
    """Try to satisfy one CostGroup. Returns chosen dice or None."""
    if group.is_pts:
        return _try_pts(available, group)

    count = group.count  # may be None → "any number" (at least 1)

    # Collect candidates that match color and value constraints individually
    candidates: list[Die] = []
    for die in available:
        color_ok = (
            _satisfies_color(die, group)
            or (not die.is_red and group.color == COLOR_VERDE)  # re-checked in caller
            or (die.is_red and group.color != COLOR_ROJO)       # red-as-wildcard
        )
        if _satisfies_value(die, group):
            candidates.append(die)

    # Separate: green candidates (exact match) and red-as-wildcard
    exact: list[Die] = [
        d for d in candidates
        if _satisfies_color(d, group)
    ]
    red_wildcard: list[Die] = [
        d for d in candidates
        if d.is_red and group.color != COLOR_ROJO and d not in exact
    ]

    # Build pool: exact first, wildcard last
    pool = exact + red_wildcard

    if count is None:
        # "any number" — need at least 1; use as many as possible
        # For constraint satisfaction we need all chosen to obey the group constraint
        # Try max pool
        if not pool:
            return None
        # Find largest subset that satisfies the group constraint
        best: Optional[list[Die]] = None
        for n in range(len(pool), 0, -1):
            for combo in _combinations(pool, n):
                if _satisfies_constraint_group([d.value for d in combo], group.constraint):
                    best = list(combo)
                    break
            if best:
                break
        return best

    # Fixed count
    if len(pool) < count:
        return None

    # Try all ordered subsets of size `count` to find one satisfying constraint
    for combo in _combinations(pool, count):
        if _satisfies_constraint_group([d.value for d in combo], group.constraint):
            return list(combo)

    return None


def _combinations(items: list, r: int):
    """Yield all unique ordered combinations of size r from items."""
    from itertools import combinations
    yield from combinations(items, r)


# ---------------------------------------------------------------------------
# Full option satisfaction (groups connected by "+")
# ---------------------------------------------------------------------------

def _try_option(roll: DiceRoll, option: CostOption) -> Optional[list[Die]]:
    """Try to satisfy all groups in an option using the dice roll.

    Returns the list of consumed dice in option-group order, or None.
    The red die is used as wildcard for non-red slots only when needed.
    """
    available = list(roll.dice)
    consumed: list[Die] = []

    for group in option:
        chosen = _try_group(available, group)
        if chosen is None:
            return None
        for die in chosen:
            available.remove(die)
        consumed.extend(chosen)

    return consumed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def can_pay(roll: DiceRoll, cost: ParsedCost) -> bool:
    """Return True if the roll can satisfy at least one cost option."""
    if not cost:
        return False
    return any(_try_option(roll, option) is not None for option in cost)


def assign_dice(roll: DiceRoll, cost: ParsedCost) -> Optional[Assignment]:
    """Return the first satisfying assignment, or None if cost cannot be paid."""
    if not cost:
        return None
    for idx, option in enumerate(cost):
        result = _try_option(roll, option)
        if result is not None:
            return Assignment(dice=result, option_index=idx)
    return None
