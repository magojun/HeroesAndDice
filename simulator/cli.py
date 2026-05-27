"""
G4 — CLI del simulador.

    python -m simulator.cli [--n-games N] [--seed S] [--output-dir DIR]
                             [--n-replays K] [--no-replays]
                             [--source sample|yaml]
                             [--set base]

Ejecuta round-robin con el pool de equipos de referencia y exporta
todo el contrato JSON que consume el frontend:

    <output-dir>/balance_report.json
    <output-dir>/catalog.json
    <output-dir>/games_index.json
    <output-dir>/games/<game_id>.json   (K muestras)

Default output-dir: frontend/data
Default source: sample (hardcodeado). Usá --source yaml para alimentarte
de docs/cards/*.yaml (requiere que el YAML tenga datos válidos; G10).
"""
from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

from ai.greedy_policy import GreedyPolicy
from simulator.metrics import compute_stats
from simulator.runner import run_batch
from simulator.report import round_robin
from simulator.tracer import GameTracer
from simulator.exporter import (
    export_balance_report, export_catalog,
    export_game_replay, export_games_index,
)
from simulator.sample_teams import get_reference_pool, SAMPLE_CATALOG


def _resolve_pool_and_catalog(source: str, set_filter: str | None):
    """
    Devuelve (pool, catalog_dict).

    source='sample': pool y catálogo hardcodeados (estable, sin deps externas).
    source='yaml':   pool y catálogo desde docs/cards/*.yaml (bridge G10).
    """
    if source == "yaml":
        from simulator.team_factory import get_pool_from_yaml, build_catalog_from_yaml
        pool = get_pool_from_yaml(set_filter=set_filter)
        catalog = build_catalog_from_yaml(set_filter=set_filter)
        return pool, catalog
    # default: sample hardcodeado
    return get_reference_pool(), {
        "heroes": SAMPLE_CATALOG["heroes"],
        "items":  SAMPLE_CATALOG["items"],
        "beasts": SAMPLE_CATALOG["beasts"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generador de datos para el frontend de Heroes y Dados"
    )
    parser.add_argument("--n-games", type=int, default=300,
                        help="Partidas por matchup (default 300)")
    parser.add_argument("--seed", type=int, default=2024,
                        help="Semilla base (default 2024)")
    parser.add_argument("--output-dir", type=str, default="frontend/data",
                        help="Carpeta de salida (default frontend/data)")
    parser.add_argument("--n-replays", type=int, default=3,
                        help="Cantidad de replays a exportar por matchup (default 3)")
    parser.add_argument("--no-replays", action="store_true",
                        help="Saltear la generación de replays individuales")
    parser.add_argument("--source", choices=["sample", "yaml"], default="sample",
                        help="Origen de héroes/objetos/bestias (default sample). "
                             "'yaml' lee docs/cards/*.yaml vía el bridge G10.")
    parser.add_argument("--set", dest="set_filter", type=str, default=None,
                        help="Filtrar a un solo set (ej: 'base'). Solo aplica con --source yaml.")
    args = parser.parse_args(argv)

    out = Path(args.output_dir)
    policy = GreedyPolicy()

    try:
        pool, catalog_data = _resolve_pool_and_catalog(args.source, args.set_filter)
    except (FileNotFoundError, ValueError) as e:
        print(f"[error] No se pudo cargar el pool con --source {args.source}: {e}")
        return 2

    if len(pool) < 2:
        print(f"[error] Necesitás al menos 2 equipos para round-robin "
              f"(pool actual: {len(pool)})")
        return 2

    print(f"[run] Source: {args.source}"
          + (f" (set={args.set_filter})" if args.set_filter else ""))

    print(f"[run] Pool: {[name for name, _ in pool]}")
    print(f"[run] Matchups: {len(list(combinations(pool, 2)))}")
    print(f"[run] Partidas por matchup: {args.n_games}")
    print(f"[run] Salida: {out.resolve()}")
    print()

    # -------------------------------------------------------------
    # G1 — balance_report.json
    # -------------------------------------------------------------
    print("[..] Corriendo round-robin...")
    matchup_results = round_robin(pool, policy, n_games=args.n_games,
                                  base_seed=args.seed)
    balance_path = out / "balance_report.json"
    export_balance_report(matchup_results, balance_path,
                          n_games_per_matchup=args.n_games)
    print(f"[ok] {balance_path}")

    # -------------------------------------------------------------
    # G2 — catalog.json
    # -------------------------------------------------------------
    catalog_path = out / "catalog.json"
    export_catalog(
        catalog_path,
        heroes=catalog_data["heroes"],
        items=catalog_data["items"],
        beasts=catalog_data["beasts"],
    )
    print(f"[ok] {catalog_path}  ({len(catalog_data['heroes'])} héroes, "
          f"{len(catalog_data['items'])} objetos, "
          f"{len(catalog_data['beasts'])} bestias)")

    # -------------------------------------------------------------
    # G3 — games/*.json + games_index.json
    # -------------------------------------------------------------
    if not args.no_replays and args.n_replays > 0:
        print(f"[..] Generando {args.n_replays} replays por matchup...")
        replays = []
        games_dir = out / "games"
        for offset, ((na, ta), (nb, tb)) in enumerate(combinations(pool, 2)):
            for k in range(args.n_replays):
                seed = args.seed + offset * 1000 + k
                tracer = GameTracer(ta, tb, policy, policy, seed=seed,
                                    name_a=na, name_b=nb)
                replay = tracer.run()
                export_game_replay(replay, games_dir / f"{replay.game_id}.json")
                replays.append(replay)

        index_path = out / "games_index.json"
        export_games_index(replays, index_path)
        print(f"[ok] {len(replays)} replays en {games_dir}")
        print(f"[ok] {index_path}")

    print("\n[ok] Frontend data lista. Abrir frontend/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
