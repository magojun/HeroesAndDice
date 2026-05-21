"""
Round-robin y reporte de balance — Epic D4 y D5.

D4: round_robin  → corre todos los matchups entre un pool de equipos
D5: generate_report → texto con ranking y flags de desbalance
"""
from __future__ import annotations

import csv
import io
from itertools import combinations
from typing import Optional

from engine.models import Team
from engine.turn_engine import PlayerPolicy
from simulator.metrics import MatchupStats, compute_stats
from simulator.runner import run_batch

# Umbral de winrate para marcar desbalance
IMBALANCE_THRESHOLD = 0.65


def round_robin(
    teams: list[tuple[str, Team]],
    policy: PlayerPolicy,
    n_games: int = 500,
    base_seed: int = 0,
) -> dict[tuple[str, str], MatchupStats]:
    """
    D4 — Ejecuta todas las combinaciones de matchups entre los equipos del pool.

    Args:
        teams: lista de (nombre, Team)
        policy: IA usada por ambos lados
        n_games: partidas por matchup
        base_seed: semilla base (cada matchup suma un offset)

    Returns:
        Dict con clave (name_a, name_b) → MatchupStats
    """
    results: dict[tuple[str, str], MatchupStats] = {}
    for offset, ((name_a, team_a), (name_b, team_b)) in enumerate(
        combinations(teams, 2)
    ):
        batch = run_batch(
            team_a, team_b, policy, policy,
            n=n_games,
            base_seed=base_seed + offset * n_games,
        )
        stats = compute_stats(batch, name_a=name_a, name_b=name_b)
        results[(name_a, name_b)] = stats
    return results


def generate_report(
    matchup_results: dict[tuple[str, str], MatchupStats],
    threshold: float = IMBALANCE_THRESHOLD,
) -> str:
    """
    D5 — Genera un reporte de texto con:
    - Tabla de matchups (winrate A vs B, duración media)
    - Ranking de equipos por winrate acumulado
    - Flags ⚠ DESBALANCE para equipos con winrate > threshold

    Returns:
        String multilínea listo para imprimir o guardar.
    """
    if not matchup_results:
        return "Sin resultados para reportar."

    # ----------------------------------------------------------------
    # Acumular puntos por equipo (win = 1, draw = 0.5, loss = 0)
    # ----------------------------------------------------------------
    points: dict[str, float] = {}
    games_played: dict[str, int] = {}

    for (na, nb), stats in matchup_results.items():
        for name in (na, nb):
            points.setdefault(name, 0.0)
            games_played.setdefault(name, 0)

        points[na] += stats.wins_a + 0.5 * stats.draws
        points[nb] += stats.wins_b + 0.5 * stats.draws
        games_played[na] += stats.n_games
        games_played[nb] += stats.n_games

    winrates: dict[str, float] = {
        name: points[name] / games_played[name]
        for name in points
        if games_played[name] > 0
    }

    ranking = sorted(winrates.items(), key=lambda x: x[1], reverse=True)

    # ----------------------------------------------------------------
    # Detectar flags de desbalance
    # ----------------------------------------------------------------
    imbalanced: list[str] = []
    for (na, nb), stats in matchup_results.items():
        if stats.winrate_a >= threshold:
            imbalanced.append(
                f"  ⚠ DESBALANCE: {na} gana {stats.winrate_a:.1%} vs {nb}"
            )
        if stats.winrate_b >= threshold:
            imbalanced.append(
                f"  ⚠ DESBALANCE: {nb} gana {stats.winrate_b:.1%} vs {na}"
            )

    # ----------------------------------------------------------------
    # Construir reporte
    # ----------------------------------------------------------------
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  REPORTE DE BALANCE — Heroes y Dados")
    lines.append("=" * 60)

    # Tabla de matchups
    lines.append("\n── MATCHUPS ──────────────────────────────────────────")
    lines.append(f"  {'Matchup':<30} {'WR-A':>6}  {'WR-B':>6}  {'Turnos':>7}")
    lines.append("  " + "-" * 54)
    for (na, nb), stats in sorted(matchup_results.items()):
        label = f"{na} vs {nb}"
        lines.append(
            f"  {label:<30} {stats.winrate_a:>6.1%}  {stats.winrate_b:>6.1%}"
            f"  {stats.avg_turns:>7.1f}"
        )

    # Ranking
    lines.append("\n── RANKING ───────────────────────────────────────────")
    lines.append(f"  {'#':<4} {'Equipo':<25} {'Winrate':>8}  {'Partidas':>8}")
    lines.append("  " + "-" * 48)
    for pos, (name, wr) in enumerate(ranking, 1):
        lines.append(
            f"  {pos:<4} {name:<25} {wr:>8.1%}  {games_played[name]:>8}"
        )

    # Flags de desbalance
    if imbalanced:
        lines.append("\n── FLAGS DE DESBALANCE ───────────────────────────────")
        lines.extend(imbalanced)
    else:
        lines.append(
            f"\n  ✓ Ningún equipo supera el {threshold:.0%} de winrate. Balance OK."
        )

    lines.append("=" * 60)
    return "\n".join(lines)


def export_csv(
    matchup_results: dict[tuple[str, str], MatchupStats],
) -> str:
    """Exporta los resultados a formato CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "team_a", "team_b", "n_games",
        "wins_a", "wins_b", "draws",
        "winrate_a", "winrate_b", "draw_rate",
        "avg_turns", "avg_hp_winner",
    ])
    for (na, nb), s in sorted(matchup_results.items()):
        writer.writerow([
            na, nb, s.n_games,
            s.wins_a, s.wins_b, s.draws,
            f"{s.winrate_a:.4f}", f"{s.winrate_b:.4f}", f"{s.draw_rate:.4f}",
            f"{s.avg_turns:.2f}", f"{s.avg_hp_winner:.2f}",
        ])
    return output.getvalue()
