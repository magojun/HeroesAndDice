"""
Simulator runner — Epic D.

D1: run_game   → ejecuta 1 partida con semilla reproducible
D2: run_batch  → ejecuta N partidas variando la semilla
"""
from __future__ import annotations

import copy
from typing import Callable

from engine.game import Game, GameResult
from engine.models import Team
from engine.turn_engine import PlayerPolicy


# Tipo fábrica: recibe el índice de semilla y devuelve un equipo fresco
TeamFactory = Callable[[int], Team]


def run_game(
    team_a: Team,
    team_b: Team,
    policy_a: PlayerPolicy,
    policy_b: PlayerPolicy,
    seed: int,
) -> GameResult:
    """
    D1 — Ejecuta una partida completa con semilla reproducible.

    Hace deep-copy de los equipos para que la función sea pura (no muta
    el estado de los equipos originales).
    """
    return Game(
        copy.deepcopy(team_a),
        copy.deepcopy(team_b),
        policy_a,
        policy_b,
        seed=seed,
    ).run()


def run_batch(
    team_a: Team,
    team_b: Team,
    policy_a: PlayerPolicy,
    policy_b: PlayerPolicy,
    n: int = 1000,
    base_seed: int = 0,
) -> list[GameResult]:
    """
    D2 — Ejecuta N partidas entre team_a y team_b.

    Cada partida usa seed = base_seed + i, garantizando reproducibilidad
    del batch completo.
    """
    return [
        run_game(team_a, team_b, policy_a, policy_b, seed=base_seed + i)
        for i in range(n)
    ]
