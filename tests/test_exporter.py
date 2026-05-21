"""Tests para Epic G — exporters Python (G1, G2, G3)."""
import json
import sys, os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from engine.models import Team, Hero, Ability
from ai.greedy_policy import GreedyPolicy
from simulator.runner import run_batch
from simulator.metrics import compute_stats
from simulator.report import round_robin
from simulator.tracer import GameTracer
from simulator.exporter import (
    build_balance_report, export_balance_report,
    build_catalog, export_catalog,
    export_game_replay, export_games_index, build_games_index,
)
from simulator.sample_teams import get_reference_pool, SAMPLE_CATALOG


POLICY = GreedyPolicy()


def _mini_team(name="T", damage=2, hp=12):
    h = Hero(name=name, max_hp=hp, shields=1,
             abilities=[Ability(name="atk", dice_cost=[3], damage=damage)])
    return Team(heroes=[h])


# ---------------------------------------------------------------------------
# G1 — balance_report.json
# ---------------------------------------------------------------------------

class TestBalanceReportExport:
    def test_build_has_required_fields(self):
        teams = [("A", _mini_team("A")), ("B", _mini_team("B"))]
        rr = round_robin(teams, POLICY, n_games=10, base_seed=1)
        report = build_balance_report(rr, n_games_per_matchup=10)

        assert "generated_at" in report
        assert "n_games_per_matchup" in report
        assert "imbalance_threshold" in report
        assert report["n_games_per_matchup"] == 10
        assert len(report["ranking"]) == 2
        assert len(report["matchups"]) == 1

    def test_ranking_sorted_desc(self):
        teams = [
            ("Strong", _mini_team("S", damage=6, hp=20)),
            ("Weak",   _mini_team("W", damage=1, hp=8)),
        ]
        rr = round_robin(teams, POLICY, n_games=30, base_seed=0)
        report = build_balance_report(rr, n_games_per_matchup=30)
        ranks = [r["rank"] for r in report["ranking"]]
        winrates = [r["winrate"] for r in report["ranking"]]
        assert ranks == [1, 2]
        assert winrates[0] >= winrates[1]

    def test_matchup_has_imbalance_flag(self):
        teams = [
            ("Mega", _mini_team("M", damage=10, hp=30)),
            ("Mini", _mini_team("m", damage=1, hp=5)),
        ]
        rr = round_robin(teams, POLICY, n_games=30, base_seed=0)
        report = build_balance_report(rr, n_games_per_matchup=30, threshold=0.6)
        assert report["matchups"][0]["imbalance_flag"] is True

    def test_writes_valid_json_file(self, tmp_path):
        teams = [("A", _mini_team("A")), ("B", _mini_team("B"))]
        rr = round_robin(teams, POLICY, n_games=10, base_seed=0)
        path = tmp_path / "balance.json"
        export_balance_report(rr, path, n_games_per_matchup=10)
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "ranking" in data
        assert "matchups" in data


# ---------------------------------------------------------------------------
# G2 — catalog.json
# ---------------------------------------------------------------------------

class TestCatalogExport:
    def test_build_empty(self):
        c = build_catalog()
        assert c["heroes"] == []
        assert c["items"] == []
        assert c["beasts"] == []
        assert "generated_at" in c

    def test_build_with_sample(self):
        c = build_catalog(
            heroes=SAMPLE_CATALOG["heroes"],
            items=SAMPLE_CATALOG["items"],
            beasts=SAMPLE_CATALOG["beasts"],
        )
        assert len(c["heroes"]) >= 3
        assert len(c["items"]) >= 3
        assert len(c["beasts"]) >= 3
        # Verificar campos del schema
        h0 = c["heroes"][0]
        assert "id" in h0 and "name" in h0 and "abilities" in h0

    def test_writes_file(self, tmp_path):
        path = tmp_path / "cat.json"
        export_catalog(path,
                       heroes=SAMPLE_CATALOG["heroes"],
                       items=SAMPLE_CATALOG["items"],
                       beasts=SAMPLE_CATALOG["beasts"])
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["heroes"]) >= 3


# ---------------------------------------------------------------------------
# G3 — game tracer + replay export
# ---------------------------------------------------------------------------

class TestGameReplay:
    def test_tracer_produces_turns(self):
        a, b = _mini_team("A"), _mini_team("B")
        tracer = GameTracer(a, b, POLICY, POLICY, seed=42,
                            name_a="A", name_b="B")
        replay = tracer.run()
        assert replay.total_turns >= 1
        assert len(replay.turns) >= 1
        assert replay.winner in ("A", "B", None)

    def test_turn_has_dice_breakdown(self):
        a, b = _mini_team("A"), _mini_team("B")
        replay = GameTracer(a, b, POLICY, POLICY, seed=1, name_a="A", name_b="B").run()
        t = replay.turns[0]
        assert len(t.green_dice) == 4
        assert 1 <= t.red_die <= 6

    def test_turn_has_state_snapshot(self):
        a, b = _mini_team("A"), _mini_team("B")
        replay = GameTracer(a, b, POLICY, POLICY, seed=1, name_a="A", name_b="B").run()
        t0 = replay.turns[0]
        assert "team_a" in t0.state_after
        assert "team_b" in t0.state_after
        assert "hp" in t0.state_after["team_a"]
        assert "diamonds" in t0.state_after["team_a"]

    def test_replay_serializes_to_json(self, tmp_path):
        a, b = _mini_team("A"), _mini_team("B")
        replay = GameTracer(a, b, POLICY, POLICY, seed=1, name_a="A", name_b="B").run()
        path = tmp_path / "replay.json"
        export_game_replay(replay, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["team_a"] == "A"
        assert data["team_b"] == "B"
        assert "turns" in data
        assert "winner" in data

    def test_reproducible_with_seed(self):
        a, b = _mini_team("A"), _mini_team("B")
        r1 = GameTracer(a, b, POLICY, POLICY, seed=7, name_a="A", name_b="B").run()
        r2 = GameTracer(a, b, POLICY, POLICY, seed=7, name_a="A", name_b="B").run()
        assert r1.total_turns == r2.total_turns
        assert r1.winner == r2.winner

    def test_games_index_export(self, tmp_path):
        a, b = _mini_team("A"), _mini_team("B")
        replays = [
            GameTracer(a, b, POLICY, POLICY, seed=s, name_a="A", name_b="B").run()
            for s in range(3)
        ]
        path = tmp_path / "idx.json"
        export_games_index(replays, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["games"]) == 3
        assert "game_id" in data["games"][0]


# ---------------------------------------------------------------------------
# G4 — CLI smoke test
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_runs_end_to_end(self, tmp_path):
        from simulator.cli import main
        out = tmp_path / "data"
        exit_code = main([
            "--n-games", "5",
            "--seed", "1",
            "--output-dir", str(out),
            "--n-replays", "1",
        ])
        assert exit_code == 0
        assert (out / "balance_report.json").exists()
        assert (out / "catalog.json").exists()
        assert (out / "games_index.json").exists()
        # Al menos un replay
        replay_files = list((out / "games").glob("*.json"))
        assert len(replay_files) >= 1

    def test_cli_no_replays_flag(self, tmp_path):
        from simulator.cli import main
        out = tmp_path / "data"
        exit_code = main([
            "--n-games", "5",
            "--output-dir", str(out),
            "--no-replays",
        ])
        assert exit_code == 0
        assert (out / "balance_report.json").exists()
        # games_index no se genera si --no-replays
        assert not (out / "games_index.json").exists()
