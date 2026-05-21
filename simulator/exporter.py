"""
Serializadores a JSON para el frontend (G1, G2, G3-serializer).

Contrato de salida:
  frontend/data/balance_report.json     ← G1
  frontend/data/catalog.json            ← G2
  frontend/data/games/<game_id>.json    ← G3
  frontend/data/games_index.json        ← G3
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from simulator.metrics import MatchupStats
from simulator.report import IMBALANCE_THRESHOLD
from simulator.tracer import GameReplay


# ---------------------------------------------------------------------------
# G1 — balance_report.json
# ---------------------------------------------------------------------------

def build_balance_report(
    matchup_results: dict[tuple[str, str], MatchupStats],
    n_games_per_matchup: int,
    threshold: float = IMBALANCE_THRESHOLD,
) -> dict:
    """Construye el dict serializable del reporte de balance."""
    # Acumular puntos por equipo (win=1, draw=0.5, loss=0) para el ranking
    points: dict[str, float] = {}
    games: dict[str, int] = {}
    for (na, nb), s in matchup_results.items():
        for name in (na, nb):
            points.setdefault(name, 0.0)
            games.setdefault(name, 0)
        points[na] += s.wins_a + 0.5 * s.draws
        points[nb] += s.wins_b + 0.5 * s.draws
        games[na] += s.n_games
        games[nb] += s.n_games

    ranking = [
        {
            "team": name,
            "winrate": round(points[name] / games[name], 4) if games[name] else 0.0,
            "games": games[name],
            "rank": pos,
        }
        for pos, (name, _) in enumerate(
            sorted(points.items(), key=lambda x: x[1] / max(games[x[0]], 1),
                   reverse=True),
            start=1,
        )
    ]

    matchups = []
    for (na, nb), s in sorted(matchup_results.items()):
        flag = s.winrate_a >= threshold or s.winrate_b >= threshold
        matchups.append({
            "team_a": na,
            "team_b": nb,
            "n_games": s.n_games,
            "winrate_a": round(s.winrate_a, 4),
            "winrate_b": round(s.winrate_b, 4),
            "draw_rate": round(s.draw_rate, 4),
            "avg_turns": round(s.avg_turns, 2),
            "avg_hp_winner": round(s.avg_hp_winner, 2),
            "avg_hp_a": round(s.avg_hp_a, 2),
            "avg_hp_b": round(s.avg_hp_b, 2),
            "imbalance_flag": flag,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_games_per_matchup": n_games_per_matchup,
        "imbalance_threshold": threshold,
        "ranking": ranking,
        "matchups": matchups,
    }


def export_balance_report(
    matchup_results: dict[tuple[str, str], MatchupStats],
    output_path: str | Path,
    n_games_per_matchup: int,
    threshold: float = IMBALANCE_THRESHOLD,
) -> None:
    data = build_balance_report(matchup_results, n_games_per_matchup, threshold)
    _write_json(output_path, data)


# ---------------------------------------------------------------------------
# G2 — catalog.json
# ---------------------------------------------------------------------------

def build_catalog(
    heroes: Iterable[dict] = (),
    items: Iterable[dict] = (),
    beasts: Iterable[dict] = (),
) -> dict:
    """
    Construye el catálogo a partir de listas de dicts.

    Cuando se conecte el card loader real (Epic A), pasar el resultado del
    loader directamente. Por ahora la CLI puede usar un sample hardcodeado
    porque docs/cards/ está gitignored.
    """
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "heroes": list(heroes),
        "items": list(items),
        "beasts": list(beasts),
    }


def export_catalog(
    output_path: str | Path,
    heroes: Iterable[dict] = (),
    items: Iterable[dict] = (),
    beasts: Iterable[dict] = (),
) -> None:
    _write_json(output_path, build_catalog(heroes, items, beasts))


# ---------------------------------------------------------------------------
# G3 — games/*.json + games_index.json
# ---------------------------------------------------------------------------

def export_game_replay(replay: GameReplay, output_path: str | Path) -> None:
    _write_json(output_path, replay.to_dict())


def build_games_index(replays: list[GameReplay]) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "games": [
            {
                "game_id": r.game_id,
                "team_a": r.team_a,
                "team_b": r.team_b,
                "seed": r.seed,
                "winner": r.winner,
                "total_turns": r.total_turns,
                "is_draw": r.is_draw,
            }
            for r in replays
        ],
    }


def export_games_index(replays: list[GameReplay], output_path: str | Path) -> None:
    _write_json(output_path, build_games_index(replays))


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _write_json(path: str | Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
