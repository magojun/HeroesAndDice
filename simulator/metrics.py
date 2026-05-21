"""
Métricas por matchup — Epic D3.

Calcula winrate, duración promedio y HP promedio restante del ganador
sobre una lista de GameResult.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.game import GameResult


@dataclass
class MatchupStats:
    name_a: str
    name_b: str
    n_games: int

    wins_a: int
    wins_b: int
    draws: int

    winrate_a: float          # fracción [0,1]
    winrate_b: float
    draw_rate: float

    avg_turns: float
    avg_hp_winner: float      # HP medio restante del ganador (0 si empate)
    avg_hp_a: float           # HP medio restante de A al final de cada partida
    avg_hp_b: float           # HP medio restante de B al final de cada partida


def compute_stats(
    results: list[GameResult],
    name_a: str = "Team A",
    name_b: str = "Team B",
) -> MatchupStats:
    """
    D3 — Calcula MatchupStats a partir de una lista de GameResult.

    Nota: GameResult.winner es una referencia al objeto Team; como
    run_batch hace deep-copy, la identidad no puede usarse directamente.
    Se infiere el ganador por hp_remaining: gana A si team_a_hp > 0 y
    team_b_hp == 0, o por el campo is_draw.
    """
    n = len(results)
    if n == 0:
        raise ValueError("La lista de resultados está vacía")

    wins_a = wins_b = draws = 0
    total_turns = 0
    total_hp_winner = 0.0
    total_hp_a = 0.0
    total_hp_b = 0.0

    for r in results:
        total_turns += r.turns
        total_hp_a += r.team_a_hp_remaining
        total_hp_b += r.team_b_hp_remaining

        if r.is_draw:
            draws += 1
        elif r.team_a_hp_remaining > 0 and r.team_b_hp_remaining == 0:
            wins_a += 1
            total_hp_winner += r.team_a_hp_remaining
        elif r.team_b_hp_remaining > 0 and r.team_a_hp_remaining == 0:
            wins_b += 1
            total_hp_winner += r.team_b_hp_remaining
        else:
            # Límite de turnos: ganador determinado por HP y luego diamantes
            if r.team_a_hp_remaining > r.team_b_hp_remaining:
                wins_a += 1
                total_hp_winner += r.team_a_hp_remaining
            elif r.team_b_hp_remaining > r.team_a_hp_remaining:
                wins_b += 1
                total_hp_winner += r.team_b_hp_remaining
            else:
                # Diamantes como desempate — no tenemos esa info aquí,
                # contar como empate a nivel de stats
                draws += 1

    decisive = wins_a + wins_b
    return MatchupStats(
        name_a=name_a,
        name_b=name_b,
        n_games=n,
        wins_a=wins_a,
        wins_b=wins_b,
        draws=draws,
        winrate_a=wins_a / n,
        winrate_b=wins_b / n,
        draw_rate=draws / n,
        avg_turns=total_turns / n,
        avg_hp_winner=total_hp_winner / decisive if decisive > 0 else 0.0,
        avg_hp_a=total_hp_a / n,
        avg_hp_b=total_hp_b / n,
    )
