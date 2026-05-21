import pytest
from heroesydados.cards.models import Hero
from heroesydados.team.model import Team, HeroState, MAX_SHIELDS


def make_hero(id="h1", vida=10, escudo=1) -> Hero:
    return Hero(id=id, set="base", nombre=id, titulo="", raza="humano",
                vida=vida, escudo=escudo, lore="")


def test_team_life_is_sum_of_heroes():
    t = Team.from_heroes(make_hero("a", vida=16), make_hero("b", vida=12))
    assert t.life == 28


def test_team_requires_two_heroes():
    with pytest.raises(ValueError):
        Team(heroes=[HeroState(make_hero())])


def test_team_shields_sum_capped_at_3():
    t = Team.from_heroes(make_hero(escudo=2), make_hero(escudo=2))
    assert t.shields == MAX_SHIELDS  # 4 → capped at 3


def test_team_shields_exact_under_cap():
    t = Team.from_heroes(make_hero(escudo=1), make_hero(escudo=1))
    assert t.shields == 2


def test_frozen_hero_no_shields():
    t = Team.from_heroes(make_hero("a", escudo=1), make_hero("b", escudo=1))
    t.freeze_hero(0)
    assert t.shields == 1  # only hero b contributes


def test_both_frozen_no_shields():
    t = Team.from_heroes(make_hero(escudo=1), make_hero(escudo=1))
    t.freeze_hero(0)
    t.freeze_hero(1)
    assert t.shields == 0


def test_unfreeze_restores_shields():
    t = Team.from_heroes(make_hero(escudo=1), make_hero(escudo=1))
    t.freeze_hero(0)
    t.unfreeze_all()
    assert t.shields == 2


def test_take_damage_reduces_life():
    t = Team.from_heroes(make_hero(vida=10), make_hero(vida=10))
    t.take_damage(5)
    assert t.life == 15


def test_take_damage_cannot_go_below_zero():
    t = Team.from_heroes(make_hero(vida=5), make_hero(vida=5))
    t.take_damage(100)
    assert t.life == 0
    assert t.is_defeated


def test_heal_increases_life():
    t = Team.from_heroes(make_hero(vida=10), make_hero(vida=10))
    t.take_damage(6)
    t.heal(2)
    assert t.life == 16


def test_team_not_defeated_initially():
    t = Team.from_heroes(make_hero(), make_hero())
    assert not t.is_defeated
