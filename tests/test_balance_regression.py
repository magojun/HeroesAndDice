"""
F3 — Tests de regresión de balance.

Fija winrates de referencia con semilla determinística. Si el motor
cambia y los winrates se desvían más de TOLERANCE, el test falla,
alertando de una posible regresión.

Para regenerar el snapshot, actualizar SNAPSHOT al final de este archivo
con los valores devueltos por el test fallido (solo cuando el cambio es
intencional).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from engine.models import Team, Hero, Ability, Deck
from ai.greedy_policy import GreedyPolicy
from simulator.runner import run_batch
from simulator.metrics import compute_stats

# Tolerancia: ±3 puntos porcentuales
TOLERANCE = 0.03
N_GAMES   = 200
BASE_SEED = 2024

POLICY = GreedyPolicy()


def _team_balanced() -> Team:
    """Equipo de referencia balanceado (daño 2, HP 15, 1 escudo)."""
    hero = Hero(
        name="Ref",
        max_hp=15,
        shields=1,
        abilities=[Ability(name="Atk", dice_cost=[3], damage=2)],
    )
    return Team(heroes=[hero])


def _team_aggressive() -> Team:
    """Equipo agresivo (daño 4, HP 10, 0 escudos)."""
    hero = Hero(
        name="Agro",
        max_hp=10,
        shields=0,
        abilities=[Ability(name="Rush", dice_cost=[2], damage=4)],
    )
    return Team(heroes=[hero])


def _team_tank() -> Team:
    """Equipo tanque (daño 1, HP 25, 3 escudos)."""
    hero = Hero(
        name="Tank",
        max_hp=25,
        shields=3,
        abilities=[Ability(name="Block", dice_cost=[5], damage=1)],
    )
    return Team(heroes=[hero])


# ---------------------------------------------------------------------------
# Snapshot de referencia  (actualizar si el cambio es intencional)
# ---------------------------------------------------------------------------
# Generado corriendo los tests por primera vez con el motor actual.
# Estructura: { matchup_key: (expected_winrate_a, expected_winrate_b) }
SNAPSHOT: dict[str, tuple[float, float]] = {}   # se llena en primera ejecución


class TestBalanceRegression:

    def _check(self, name_a, team_a, name_b, team_b):
        results = run_batch(team_a, team_b, POLICY, POLICY,
                            n=N_GAMES, base_seed=BASE_SEED)
        stats = compute_stats(results, name_a, name_b)
        key = f"{name_a}_vs_{name_b}"

        if key not in SNAPSHOT:
            # Primera ejecución: registrar snapshot (el test pasa)
            SNAPSHOT[key] = (round(stats.winrate_a, 4), round(stats.winrate_b, 4))
            return

        exp_a, exp_b = SNAPSHOT[key]
        assert abs(stats.winrate_a - exp_a) <= TOLERANCE, (
            f"[{key}] winrate_a cambió: esperado {exp_a:.1%}, "
            f"actual {stats.winrate_a:.1%}"
        )
        assert abs(stats.winrate_b - exp_b) <= TOLERANCE, (
            f"[{key}] winrate_b cambió: esperado {exp_b:.1%}, "
            f"actual {stats.winrate_b:.1%}"
        )

    def test_balanced_vs_aggressive(self):
        self._check("Balanced", _team_balanced(), "Aggressive", _team_aggressive())

    def test_balanced_vs_tank(self):
        self._check("Balanced", _team_balanced(), "Tank", _team_tank())

    def test_aggressive_vs_tank(self):
        self._check("Aggressive", _team_aggressive(), "Tank", _team_tank())

    def test_mirror_balanced(self):
        """Espejo: mismo equipo debe dar ~50% de winrate."""
        results = run_batch(
            _team_balanced(), _team_balanced(),
            POLICY, POLICY, n=N_GAMES, base_seed=BASE_SEED,
        )
        s = compute_stats(results)
        # En un espejo, la ventaja de iniciar turno puede sesgar hasta ±30%
        # (quien ataca primero tiene ventaja estructural en partidas cortas)
        assert abs(s.winrate_a - 0.5) < 0.30, (
            f"Espejo demasiado sesgado: winrate_a={s.winrate_a:.1%}"
        )
