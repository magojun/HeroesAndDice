"""Tests para EPIC B — Motor de turno y combate."""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from engine.models import (
    Ability, Beast, Deck, Hero, Item, ItemUsage,
    StatusEffect, StatusToken, Team,
)
from engine.turn_engine import TurnContext, TurnEngine
from engine.game import Game, GameResult


# ---------------------------------------------------------------------------
# Política stub que no hace nada (para tests de bajo nivel)
# ---------------------------------------------------------------------------

class PassPolicy:
    def assign_dice(self, ctx): return []
    def choose_hunt_beast(self, ctx): return False
    def choose_buy_item(self, ctx): return False
    def choose_use_item(self, ctx, item, phase): return False
    def choose_apply_status(self, ctx): return []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_team(hp=10, shields=0, diamonds=0) -> Team:
    hero = Hero(name="TestHero", max_hp=hp, shields=shields)
    return Team(heroes=[hero], diamonds=diamonds)


# ---------------------------------------------------------------------------
# B3 — Resolución de combate
# ---------------------------------------------------------------------------

class TestCombat:
    def test_damage_reduces_defender_hp(self):
        attacker = make_team()
        defender = make_team(hp=10)
        engine = TurnEngine()

        # Forzar ctx con daño conocido y sin escudos
        ctx = TurnContext(attacker=attacker, defender=defender)
        ctx.total_damage = 5
        engine._phase_combat(ctx, PassPolicy())

        assert defender.hp <= 10
        # Con 0 escudos no hay defensa → pierde exactamente 5
        assert defender.hp == 5

    def test_shields_can_block_damage(self):
        attacker = make_team()
        defender = make_team(hp=10, shields=3)
        engine = TurnEngine()

        random.seed(42)  # semilla reproducible
        ctx = TurnContext(attacker=attacker, defender=defender)
        ctx.total_damage = 3

        engine._phase_combat(ctx, PassPolicy())

        # Con 3 escudos y semilla 42 se verifica que no pierde más de 3 vidas
        assert 7 <= defender.hp <= 10

    def test_damage_cannot_go_below_zero_hp(self):
        attacker = make_team()
        defender = make_team(hp=2)
        engine = TurnEngine()

        ctx = TurnContext(attacker=attacker, defender=defender)
        ctx.total_damage = 100
        engine._phase_combat(ctx, PassPolicy())

        assert defender.hp == 0

    def test_no_damage_skips_combat(self):
        attacker = make_team()
        defender = make_team(hp=10)
        engine = TurnEngine()

        ctx = TurnContext(attacker=attacker, defender=defender)
        ctx.total_damage = 0
        engine._phase_combat(ctx, PassPolicy())

        assert defender.hp == 10


# ---------------------------------------------------------------------------
# B4 — Fichas de estado y su timing
# ---------------------------------------------------------------------------

class TestStatusTokens:
    def test_poison_adds_extra_damage(self):
        attacker = make_team()
        defender = make_team(hp=10)
        engine = TurnEngine()

        defender.apply_status(StatusToken(effect=StatusEffect.POISON))
        ctx = TurnContext(attacker=attacker, defender=defender)
        ctx.total_damage = 2  # 2 base + 1 poison = 3 total

        engine._phase_combat(ctx, PassPolicy())
        assert defender.hp == 7

    def test_burn_adds_2_extra_damage(self):
        attacker = make_team()
        defender = make_team(hp=10)
        engine = TurnEngine()

        defender.apply_status(StatusToken(effect=StatusEffect.BURN))
        ctx = TurnContext(attacker=attacker, defender=defender)
        ctx.total_damage = 1  # 1 + 2 burn = 3

        engine._phase_combat(ctx, PassPolicy())
        assert defender.hp == 7

    def test_freeze_blocks_all_defense(self):
        attacker = make_team()
        defender = make_team(hp=10, shields=3)  # 3 escudos, pero FREEZE anula defensa
        engine = TurnEngine()

        defender.apply_status(StatusToken(effect=StatusEffect.FREEZE))
        ctx = TurnContext(attacker=attacker, defender=defender)
        ctx.total_damage = 4

        engine._phase_combat(ctx, PassPolicy())
        assert defender.hp == 6  # sin reducción por escudos

    def test_silence_blocks_abilities(self):
        ability = Ability(name="Strike", dice_cost=[3], damage=5)
        hero = Hero(name="Silenced", max_hp=10, abilities=[ability])
        attacker = Team(heroes=[hero])
        defender = make_team(hp=10)
        engine = TurnEngine()

        attacker.apply_status(StatusToken(effect=StatusEffect.SILENCE))

        class AlwaysAssignPolicy(PassPolicy):
            def assign_dice(self, ctx):
                return [("Strike", 0, [0])]

        ctx = TurnContext(attacker=attacker, defender=defender)
        ctx.dice = engine._phase_roll.__func__(engine, ctx) or ctx.dice
        engine._phase_assign(ctx, AlwaysAssignPolicy())

        assert ctx.total_damage == 0  # SILENCE bloqueó la asignación

    def test_status_expires_after_one_turn(self):
        defender = make_team()
        token = StatusToken(effect=StatusEffect.POISON, turns_remaining=1)
        defender.apply_status(token)

        expired = defender.tick_statuses()

        assert len(defender.active_statuses) == 0
        assert len(expired) == 1

    def test_status_not_expired_while_remaining(self):
        defender = make_team()
        token = StatusToken(effect=StatusEffect.BURN, turns_remaining=2)
        defender.apply_status(token)

        expired = defender.tick_statuses()

        assert len(defender.active_statuses) == 1
        assert len(expired) == 0


# ---------------------------------------------------------------------------
# B5 — Compra de objetos
# ---------------------------------------------------------------------------

class TestItemPurchase:
    def test_buy_item_deducts_diamonds(self):
        item = Item(name="Potion", cost_diamonds=3, usage=ItemUsage.SINGLE_USE)
        attacker = make_team(diamonds=5)
        attacker.visible_item = item
        engine = TurnEngine()

        class BuyPolicy(PassPolicy):
            def choose_buy_item(self, ctx): return True

        ctx = TurnContext(attacker=attacker, defender=make_team())
        engine._phase_buy(ctx, BuyPolicy())

        assert attacker.diamonds == 2
        assert item in attacker.items_owned
        assert attacker.visible_item is None

    def test_cannot_buy_without_enough_diamonds(self):
        item = Item(name="Sword", cost_diamonds=10, usage=ItemUsage.PERMANENT)
        attacker = make_team(diamonds=3)
        attacker.visible_item = item
        engine = TurnEngine()

        class BuyPolicy(PassPolicy):
            def choose_buy_item(self, ctx): return True

        ctx = TurnContext(attacker=attacker, defender=make_team())
        engine._phase_buy(ctx, BuyPolicy())

        assert attacker.diamonds == 3
        assert item not in attacker.items_owned

    def test_single_use_item_removed_after_use(self):
        item = Item(name="Bomb", cost_diamonds=0, usage=ItemUsage.SINGLE_USE, damage_bonus=3)
        attacker = make_team()
        attacker.items_owned.append(item)
        engine = TurnEngine()

        class UsePolicy(PassPolicy):
            def choose_use_item(self, ctx, item, phase): return phase == "combat"

        ctx = TurnContext(attacker=attacker, defender=make_team(hp=10))
        ctx.total_damage = 1
        engine._phase_combat(ctx, UsePolicy())

        assert item not in attacker.items_owned


# ---------------------------------------------------------------------------
# B6 — Caza de bestias
# ---------------------------------------------------------------------------

class TestBeastHunting:
    def test_hunt_awards_diamonds(self):
        beast = Beast(name="Goblin", dice_cost=[1, 2], reward_diamonds=3)
        attacker = make_team()
        attacker.visible_beast = beast
        engine = TurnEngine()

        class HuntPolicy(PassPolicy):
            def choose_hunt_beast(self, ctx): return True

        ctx = TurnContext(attacker=attacker, defender=make_team())
        engine._phase_hunt_cycle(ctx, HuntPolicy())

        assert attacker.diamonds == 3
        assert attacker.visible_beast is None

    def test_hunt_awards_hp(self):
        beast = Beast(name="Troll", dice_cost=[4], reward_hp=5)
        attacker = make_team(hp=10)
        attacker.visible_beast = beast
        engine = TurnEngine()

        class HuntPolicy(PassPolicy):
            def choose_hunt_beast(self, ctx): return True

        ctx = TurnContext(attacker=attacker, defender=make_team())
        engine._phase_hunt_cycle(ctx, HuntPolicy())

        assert attacker.hp == 15

    def test_no_hunt_cycles_item_deck(self):
        item = Item(name="Shield", cost_diamonds=2, usage=ItemUsage.PERMANENT)
        attacker = make_team()
        attacker.item_deck = Deck([item])
        engine = TurnEngine()

        ctx = TurnContext(attacker=attacker, defender=make_team())
        engine._phase_hunt_cycle(ctx, PassPolicy())

        # El ciclo mueve la carta al fondo (misma carta, mismo mazo)
        assert len(attacker.item_deck.cards) == 1


# ---------------------------------------------------------------------------
# B7 — Condición de fin de partida
# ---------------------------------------------------------------------------

class TestGameEnd:
    def test_team_b_wins_when_team_a_dies(self):
        team_a = make_team(hp=1)
        team_b = make_team(hp=10)
        engine = TurnEngine()

        # Matamos a team_a directamente
        team_a.take_damage(1)

        game = Game(team_a, team_b, PassPolicy(), PassPolicy())
        result = game._check_end(turns=1)

        assert result is not None
        assert result.winner is team_b
        assert result.is_draw is False

    def test_diamond_tiebreak_when_both_die(self):
        team_a = make_team(hp=0, diamonds=5)
        team_b = make_team(hp=0, diamonds=3)

        game = Game(team_a, team_b, PassPolicy(), PassPolicy())
        result = game._tiebreak(turns=10)

        assert result.winner is team_a
        assert result.is_draw is False

    def test_true_draw_when_equal_diamonds(self):
        team_a = make_team(hp=0, diamonds=4)
        team_b = make_team(hp=0, diamonds=4)

        game = Game(team_a, team_b, PassPolicy(), PassPolicy())
        result = game._tiebreak(turns=10)

        assert result.is_draw is True

    def test_full_game_runs_and_returns_result(self):
        team_a = make_team(hp=5)
        team_b = make_team(hp=5)

        random.seed(0)
        result = Game(team_a, team_b, PassPolicy(), PassPolicy(), seed=0).run()

        assert isinstance(result, GameResult)
        # Con PassPolicy nadie inflige daño → llega al límite de turnos, se resuelve por HP/diamantes
        assert result.turns == Game.MAX_TURNS or result.is_draw

    def test_game_result_contains_metrics(self):
        team_a = make_team(hp=10, diamonds=2)
        team_b = make_team(hp=10, diamonds=5)
        team_a.take_damage(10)

        game = Game(team_a, team_b, PassPolicy(), PassPolicy())
        result = game._check_end(1)

        assert result.team_a_hp_remaining == 0
        assert result.team_b_hp_remaining == 10
        assert result.team_b_diamonds == 5
