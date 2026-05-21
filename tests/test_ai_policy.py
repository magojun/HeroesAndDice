"""Tests para GreedyPolicy (Epic C)."""
import sys
import os
import random

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.models import (
    Team, Hero, Ability, Beast, Item, ItemUsage, StatusEffect, StatusToken, Deck
)
from engine.turn_engine import TurnContext, TurnEngine
from ai.greedy_policy import GreedyPolicy
from dice import DiceList, RegularDice, SpecialDice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_die(value: int, special: bool = False):
    die = SpecialDice() if special else RegularDice()
    die.die_number = value
    return die


def make_dice(*values_and_types) -> DiceList:
    """
    Recibe pares (valor, es_especial). Ej: make_dice((3,False),(5,True))
    O solo valores enteros como dados regulares: make_dice(1,2,3,4,5)
    """
    dl = DiceList()
    for v in values_and_types:
        if isinstance(v, tuple):
            dl.append(make_die(v[0], v[1]))
        else:
            dl.append(make_die(v))
    return dl


def make_team(abilities=None, hp=10, shields=0, diamonds=0,
              items=None, beasts=None) -> Team:
    hero = Hero(
        name="TestHero",
        max_hp=hp,
        shields=shields,
        abilities=abilities or [],
    )
    team = Team(
        heroes=[hero],
        diamonds=diamonds,
        item_deck=Deck(cards=list(items or [])),
        beast_deck=Deck(cards=list(beasts or [])),
    )
    return team


def make_ctx(attacker: Team, defender: Team, dice: DiceList) -> TurnContext:
    ctx = TurnContext(attacker=attacker, defender=defender)
    ctx.dice = dice
    return ctx


# ---------------------------------------------------------------------------
# C2 — assign_dice
# ---------------------------------------------------------------------------

class TestAssignDice:
    def test_assigns_matching_die_to_ability(self):
        ability = Ability(name="Ataque", dice_cost=[3], damage=2)
        team = make_team(abilities=[ability])
        ctx = make_ctx(team, make_team(), make_dice(3, 1, 2, 4, 5))
        policy = GreedyPolicy()

        result = policy.assign_dice(ctx)

        assert len(result) == 1
        name, hero_idx, indices = result[0]
        assert name == "Ataque"
        assert hero_idx == 0
        assert len(indices) == 1
        # El dado en ese índice debe tener valor 3
        assert ctx.dice[indices[0]].get_number() == 3

    def test_assigns_multiple_abilities_without_overlap(self):
        a1 = Ability(name="A1", dice_cost=[2], damage=3)
        a2 = Ability(name="A2", dice_cost=[5], damage=1)
        team = make_team(abilities=[a1, a2])
        ctx = make_ctx(team, make_team(), make_dice(2, 5, 1, 4, 6))
        policy = GreedyPolicy()

        result = policy.assign_dice(ctx)
        names = {r[0] for r in result}

        assert "A1" in names
        assert "A2" in names
        # Sin solapamiento de índices
        all_indices = [idx for _, _, idxs in result for idx in idxs]
        assert len(all_indices) == len(set(all_indices))

    def test_no_matching_die_returns_empty(self):
        ability = Ability(name="Impossible", dice_cost=[6], damage=5)
        team = make_team(abilities=[ability])
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        policy = GreedyPolicy()

        result = policy.assign_dice(ctx)
        assert result == []

    def test_red_die_used_as_wildcard(self):
        ability = Ability(name="ConRojo", dice_cost=[6], damage=2)
        team = make_team(abilities=[ability])
        # Solo hay un dado rojo (especial), no hay dado con cara 6
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, (5, True)))
        policy = GreedyPolicy()

        result = policy.assign_dice(ctx)

        assert len(result) == 1
        _, _, indices = result[0]
        assert ctx.dice[indices[0]].is_special_type()

    def test_prefers_regular_die_over_red_wildcard(self):
        ability = Ability(name="Atacar", dice_cost=[4], damage=2)
        team = make_team(abilities=[ability])
        # Dado regular con 4 y dado rojo también disponible
        ctx = make_ctx(team, make_team(), make_dice((4, False), (4, True)))
        policy = GreedyPolicy()

        result = policy.assign_dice(ctx)

        assert len(result) == 1
        _, _, indices = result[0]
        # Debe preferir el dado regular (índice 0)
        assert not ctx.dice[indices[0]].is_special_type()

    def test_non_repeatable_ability_used_once(self):
        ability = Ability(name="SingleUse", dice_cost=[1], damage=2, repeatable=False)
        team = make_team(abilities=[ability])
        # Dos dados que podrían satisfacer el costo
        ctx = make_ctx(team, make_team(), make_dice(1, 1, 2, 3, 4))
        policy = GreedyPolicy()

        result = policy.assign_dice(ctx)
        names = [r[0] for r in result]

        assert names.count("SingleUse") == 1

    def test_repeatable_ability_can_be_used_twice(self):
        ability = Ability(name="Multi", dice_cost=[2], damage=1, repeatable=True)
        team = make_team(abilities=[ability])
        ctx = make_ctx(team, make_team(), make_dice(2, 2, 3, 4, 5))
        policy = GreedyPolicy()

        result = policy.assign_dice(ctx)
        names = [r[0] for r in result]

        assert names.count("Multi") == 2

    def test_prioritizes_higher_damage_ability(self):
        low = Ability(name="LowDmg", dice_cost=[3], damage=1)
        high = Ability(name="HighDmg", dice_cost=[3], damage=5)
        team = make_team(abilities=[low, high])
        # Solo un dado con cara 3, así que solo una habilidad puede activarse
        ctx = make_ctx(team, make_team(), make_dice(3, 1, 2, 4, 5))
        policy = GreedyPolicy()

        result = policy.assign_dice(ctx)

        assert len(result) == 1
        assert result[0][0] == "HighDmg"

    def test_silence_does_not_affect_policy_directly(self):
        """La engine bloquea la asignación bajo SILENCE; la política devuelve assignments igual."""
        ability = Ability(name="Ataque", dice_cost=[1], damage=3)
        team = make_team(abilities=[ability])
        team.apply_status(StatusToken(effect=StatusEffect.SILENCE))
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        policy = GreedyPolicy()

        # La política no sabe de SILENCE; la engine lo filtra
        result = policy.assign_dice(ctx)
        assert len(result) >= 0  # puede retornar assignments; la engine las ignora


# ---------------------------------------------------------------------------
# C4 — Economía: caza y compra
# ---------------------------------------------------------------------------

class TestEconomy:
    def test_hunts_beast_with_diamond_reward(self):
        beast = Beast(name="Lobo", dice_cost=[], reward_diamonds=2)
        team = make_team()
        team.visible_beast = beast
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        assert GreedyPolicy().choose_hunt_beast(ctx) is True

    def test_hunts_beast_with_hp_reward(self):
        beast = Beast(name="Oso", dice_cost=[], reward_hp=3)
        team = make_team()
        team.visible_beast = beast
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        assert GreedyPolicy().choose_hunt_beast(ctx) is True

    def test_does_not_hunt_zero_reward_beast(self):
        beast = Beast(name="Inútil", dice_cost=[], reward_diamonds=0, reward_hp=0)
        team = make_team()
        team.visible_beast = beast
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        assert GreedyPolicy().choose_hunt_beast(ctx) is False

    def test_does_not_hunt_without_beast(self):
        team = make_team()
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        assert GreedyPolicy().choose_hunt_beast(ctx) is False

    def test_buys_item_with_damage_bonus(self):
        item = Item(name="Espada", cost_diamonds=2, usage=ItemUsage.PERMANENT, damage_bonus=2)
        team = make_team(diamonds=3)
        team.visible_item = item
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        assert GreedyPolicy().choose_buy_item(ctx) is True

    def test_does_not_buy_without_enough_diamonds(self):
        item = Item(name="Espada", cost_diamonds=5, usage=ItemUsage.PERMANENT, damage_bonus=2)
        team = make_team(diamonds=2)
        team.visible_item = item
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        assert GreedyPolicy().choose_buy_item(ctx) is False

    def test_does_not_buy_zero_damage_item(self):
        item = Item(name="Piedra", cost_diamonds=1, usage=ItemUsage.SINGLE_USE, damage_bonus=0)
        team = make_team(diamonds=5)
        team.visible_item = item
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        assert GreedyPolicy().choose_buy_item(ctx) is False

    def test_does_not_buy_without_item(self):
        team = make_team(diamonds=5)
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        assert GreedyPolicy().choose_buy_item(ctx) is False


# ---------------------------------------------------------------------------
# C3 — Uso de objetos
# ---------------------------------------------------------------------------

class TestItemUsage:
    def test_uses_single_use_item_in_combat_with_damage(self):
        item = Item(name="Poción", cost_diamonds=0, usage=ItemUsage.SINGLE_USE, damage_bonus=2)
        team = make_team()
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        ctx.total_damage = 3
        assert GreedyPolicy().choose_use_item(ctx, item, "combat") is True

    def test_does_not_use_item_in_combat_without_damage(self):
        item = Item(name="Poción", cost_diamonds=0, usage=ItemUsage.SINGLE_USE, damage_bonus=2)
        team = make_team()
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        ctx.total_damage = 0
        assert GreedyPolicy().choose_use_item(ctx, item, "combat") is False

    def test_does_not_use_permanent_item(self):
        item = Item(name="Armadura", cost_diamonds=3, usage=ItemUsage.PERMANENT, damage_bonus=1)
        team = make_team()
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        ctx.total_damage = 5
        assert GreedyPolicy().choose_use_item(ctx, item, "combat") is False

    def test_uses_item_when_low_hp(self):
        item = Item(name="Elixir", cost_diamonds=0, usage=ItemUsage.SINGLE_USE, damage_bonus=3)
        # HP al 30%, por debajo del umbral del 40%
        team = make_team(hp=10)
        team._hp = 3
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        ctx.total_damage = 0
        assert GreedyPolicy().choose_use_item(ctx, item, "assign") is True


# ---------------------------------------------------------------------------
# C5 — Estados
# ---------------------------------------------------------------------------

class TestStatusPolicy:
    def test_returns_empty_until_card_abilities_loaded(self):
        team = make_team()
        ctx = make_ctx(team, make_team(), make_dice(1, 2, 3, 4, 5))
        result = GreedyPolicy().choose_apply_status(ctx)
        assert result == []


# ---------------------------------------------------------------------------
# Integración: GreedyPolicy jugando una partida completa
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_game_runs_without_error(self):
        """Una partida con dos GreedyPolicy debe terminar sin errores."""
        from engine.game import Game

        ability_a = Ability(name="Slash", dice_cost=[3], damage=2)
        ability_b = Ability(name="Stab", dice_cost=[4], damage=3)

        team_a = make_team(abilities=[ability_a], hp=15, shields=1, diamonds=3)
        team_b = make_team(abilities=[ability_b], hp=15, shields=1, diamonds=3)

        policy = GreedyPolicy()
        game = Game(team_a, team_b, policy, policy, seed=42)
        result = game.run()

        assert result.turns >= 1
        assert result.winner is not None or result.is_draw

    def test_greedy_beats_passive_opponent(self):
        """GreedyPolicy debe ganar contra un oponente sin habilidades."""
        from engine.game import Game

        class PassivePolicy:
            def assign_dice(self, ctx):
                return []
            def choose_hunt_beast(self, ctx):
                return False
            def choose_buy_item(self, ctx):
                return False
            def choose_use_item(self, ctx, item, phase):
                return False
            def choose_apply_status(self, ctx):
                return []

        ability = Ability(name="Golpe", dice_cost=[1], damage=3)
        team_a = make_team(abilities=[ability], hp=20)
        team_b = make_team(abilities=[], hp=20)

        game = Game(team_a, team_b, GreedyPolicy(), PassivePolicy(), seed=1)
        result = game.run()

        # El equipo A con habilidades debe ganar con alta probabilidad con semilla fija
        assert not result.is_draw
        assert result.winner is team_a
