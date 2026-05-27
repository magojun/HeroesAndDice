import pytest
from heroesydados.cards.loader import load_heroes, load_beasts, load_objects
from heroesydados.cards.models import Hero, Beast, MagicObject


def test_load_heroes_returns_list():
    heroes = load_heroes()
    assert len(heroes) > 0
    assert all(isinstance(h, Hero) for h in heroes)


def test_load_heroes_set_field():
    heroes = load_heroes()
    assert all(h.set for h in heroes)


def test_load_heroes_filter_base():
    heroes = load_heroes(set_filter="base")
    assert len(heroes) == 8
    assert all(h.set == "base" for h in heroes)


def test_load_heroes_unknown_set_returns_empty():
    heroes = load_heroes(set_filter="expansion_inexistente")
    assert heroes == []


def test_hero_has_skills_and_passives():
    heroes = load_heroes()
    mrhan = next(h for h in heroes if h.id == "mrhan")
    assert mrhan.vida == 16
    assert mrhan.escudo == 0
    assert len(mrhan.habilidades) == 4
    assert len(mrhan.destrezas) == 1


def test_hero_confirmar_tolerated():
    """El loader tolera el campo confirmar:true sin crashear y lo expone como bool.

    No asumimos cuántas entradas hay con confirmar:true (van bajando a medida
    que el usuario las valida). Sólo verificamos que el campo se respeta cuando
    está presente, y que skills sin costo solo se aceptan si están marcadas
    confirmar (o ya transcriptas).
    """
    heroes = load_heroes()
    # El campo confirmar siempre debe ser bool (default False)
    for h in heroes:
        for s in h.habilidades:
            assert isinstance(s.confirmar, bool)
            # Skills con costo=None deben estar marcadas confirmar
            # (o ser tolerablemente ambiguas — política del proyecto)
            if s.costo is None:
                assert s.confirmar, (
                    f"Skill «{s.nombre}» de {h.nombre} tiene costo=None "
                    f"pero no está marcada confirmar:true"
                )


def test_skill_with_null_costo_tolerated():
    heroes = load_heroes()
    morios = next(h for h in heroes if h.id == "morios")
    aliento = next(s for s in morios.habilidades if s.nombre == "Aliento Abrasivo")
    assert aliento.costo is None
    assert aliento.confirmar is True


def test_load_beasts():
    beasts = load_beasts()
    assert len(beasts) == 2
    assert all(isinstance(b, Beast) for b in beasts)


def test_beasts_set_filter():
    beasts = load_beasts(set_filter="base")
    assert len(beasts) == 2


def test_load_objects():
    objects = load_objects()
    assert len(objects) > 0
    assert all(isinstance(o, MagicObject) for o in objects)


def test_objects_set_filter():
    objects = load_objects(set_filter="base")
    assert len(objects) == 15
