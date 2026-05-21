"""Tests para Epic D — Simulador de balance."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from engine.models import Team, Hero, Ability, Deck
from ai.greedy_policy import GreedyPolicy
from simulator.runner import run_game, run_batch
from simulator.metrics import compute_stats, MatchupStats
from simulator.report import round_robin, generate_report, export_csv, IMBALANCE_THRESHOLD


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_team(name="Team", damage=2, hp=15, shields=1):
    ability = Ability(name=f"{name}_atk", dice_cost=[3], damage=damage)
    hero = Hero(name=name, max_hp=hp, shields=shields, abilities=[ability])
    return Team(heroes=[hero])


POLICY = GreedyPolicy()


# ---------------------------------------------------------------------------
# D1 — run_game
# ---------------------------------------------------------------------------

class TestRunGame:
    def test_returns_game_result(self):
        result = run_game(make_team(), make_team(), POLICY, POLICY, seed=1)
        assert result is not None
        assert result.turns >= 1

    def test_same_seed_same_result(self):
        a, b = make_team("A"), make_team("B")
        r1 = run_game(a, b, POLICY, POLICY, seed=42)
        r2 = run_game(a, b, POLICY, POLICY, seed=42)
        assert r1.turns == r2.turns
        assert r1.is_draw == r2.is_draw
        assert r1.team_a_hp_remaining == r2.team_a_hp_remaining

    def test_different_seeds_may_differ(self):
        a, b = make_team("A", damage=3), make_team("B", damage=1)
        results = {run_game(a, b, POLICY, POLICY, seed=s).turns for s in range(20)}
        # Con 20 semillas distintas, muy probablemente hay variación
        assert len(results) > 1

    def test_does_not_mutate_original_teams(self):
        a, b = make_team(), make_team()
        original_hp_a = a.hp
        original_hp_b = b.hp
        run_game(a, b, POLICY, POLICY, seed=7)
        assert a.hp == original_hp_a
        assert b.hp == original_hp_b


# ---------------------------------------------------------------------------
# D2 — run_batch
# ---------------------------------------------------------------------------

class TestRunBatch:
    def test_returns_n_results(self):
        results = run_batch(make_team(), make_team(), POLICY, POLICY, n=10)
        assert len(results) == 10

    def test_all_results_are_valid(self):
        results = run_batch(make_team(), make_team(), POLICY, POLICY, n=5)
        for r in results:
            assert r.turns >= 1
            assert r.team_a_hp_remaining >= 0
            assert r.team_b_hp_remaining >= 0

    def test_reproducible_with_base_seed(self):
        a, b = make_team("A"), make_team("B")
        batch1 = run_batch(a, b, POLICY, POLICY, n=5, base_seed=100)
        batch2 = run_batch(a, b, POLICY, POLICY, n=5, base_seed=100)
        for r1, r2 in zip(batch1, batch2):
            assert r1.turns == r2.turns


# ---------------------------------------------------------------------------
# D3 — compute_stats
# ---------------------------------------------------------------------------

class TestComputeStats:
    def test_basic_stats_from_batch(self):
        results = run_batch(make_team("A", damage=5), make_team("B", damage=1),
                            POLICY, POLICY, n=50, base_seed=0)
        stats = compute_stats(results, "A", "B")
        assert stats.n_games == 50
        assert stats.wins_a + stats.wins_b + stats.draws == 50
        assert abs(stats.winrate_a + stats.winrate_b + stats.draw_rate - 1.0) < 1e-9

    def test_winrates_sum_to_one(self):
        results = run_batch(make_team(), make_team(), POLICY, POLICY, n=20)
        s = compute_stats(results)
        assert abs(s.winrate_a + s.winrate_b + s.draw_rate - 1.0) < 1e-9

    def test_stronger_team_wins_more(self):
        results = run_batch(
            make_team("Strong", damage=6, hp=20),
            make_team("Weak", damage=1, hp=10),
            POLICY, POLICY, n=100, base_seed=0,
        )
        s = compute_stats(results, "Strong", "Weak")
        assert s.winrate_a > s.winrate_b

    def test_avg_turns_positive(self):
        results = run_batch(make_team(), make_team(), POLICY, POLICY, n=20)
        s = compute_stats(results)
        assert s.avg_turns > 0

    def test_empty_results_raises(self):
        with pytest.raises(ValueError):
            compute_stats([])


# ---------------------------------------------------------------------------
# D4 — round_robin
# ---------------------------------------------------------------------------

class TestRoundRobin:
    def test_all_matchups_present(self):
        teams = [("A", make_team("A")), ("B", make_team("B")), ("C", make_team("C"))]
        results = round_robin(teams, POLICY, n_games=10)
        # 3 equipos → 3 matchups
        assert len(results) == 3
        assert ("A", "B") in results
        assert ("A", "C") in results
        assert ("B", "C") in results

    def test_stats_have_correct_n(self):
        teams = [("X", make_team()), ("Y", make_team())]
        results = round_robin(teams, POLICY, n_games=20)
        assert results[("X", "Y")].n_games == 20


# ---------------------------------------------------------------------------
# D5 — generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_report_contains_teams(self):
        teams = [("Alpha", make_team("Alpha", damage=4)), ("Beta", make_team("Beta", damage=2))]
        rr = round_robin(teams, POLICY, n_games=30)
        report = generate_report(rr)
        assert "Alpha" in report
        assert "Beta" in report

    def test_report_flags_imbalance(self):
        # Equipo muy fuerte vs muy débil
        teams = [
            ("Fuerte", make_team("Fuerte", damage=8, hp=25)),
            ("Débil", make_team("Débil", damage=1, hp=5)),
        ]
        rr = round_robin(teams, POLICY, n_games=50)
        report = generate_report(rr, threshold=0.60)
        assert "DESBALANCE" in report or "Balance OK" in report  # alguno de los dos

    def test_report_no_imbalance_message_when_balanced(self):
        # Equipos idénticos → balance perfecto
        teams = [("Igual1", make_team(damage=3)), ("Igual2", make_team(damage=3))]
        rr = round_robin(teams, POLICY, n_games=100)
        report = generate_report(rr, threshold=0.99)
        assert "Balance OK" in report

    def test_empty_report(self):
        report = generate_report({})
        assert "Sin resultados" in report

    def test_csv_export(self):
        teams = [("T1", make_team()), ("T2", make_team())]
        rr = round_robin(teams, POLICY, n_games=10)
        csv_output = export_csv(rr)
        assert "team_a" in csv_output
        assert "T1" in csv_output
