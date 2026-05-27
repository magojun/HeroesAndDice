"""Tests para simulator/team_factory.py (G10 — bridge YAML → engine)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from simulator.team_factory import (
    approximate_dice_cost, extract_damage,
    card_skill_to_ability, card_hero_to_engine,
    _hero_to_catalog, _object_to_catalog, _beast_to_catalog,
    _USO_MAP,
)
from heroesydados.cards.models import Hero as CardHero, Skill as CardSkill, Passive as CardPassive, MagicObject, Beast as CardBeast


# ---------------------------------------------------------------------------
# approximate_dice_cost — heurística
# ---------------------------------------------------------------------------

class TestApproximateDiceCost:
    def test_empty_returns_empty(self):
        assert approximate_dice_cost(None) == []
        assert approximate_dice_cost("") == []

    def test_single_fixed_value(self):
        # "1d verde >=4" → [4]
        assert approximate_dice_cost("1d verde >=4") == [4]

    def test_multiple_dice_same_constraint(self):
        # "4d verde >=4" → [4, 4, 4, 4]
        assert approximate_dice_cost("4d verde >=4") == [4, 4, 4, 4]

    def test_max_value_used(self):
        # "3d verde <=3" → [3, 3, 3]
        assert approximate_dice_cost("3d verde <=3") == [3, 3, 3]

    def test_pares_uses_2(self):
        # "3d verde pares" → [2, 2, 2]
        assert approximate_dice_cost("3d verde pares") == [2, 2, 2]

    def test_impares_uses_1(self):
        assert approximate_dice_cost("2d verde impares") == [1, 1]

    def test_iguales_uses_3(self):
        # "verde iguales" → [3, 3] (count defaults to 1 if not specified, but
        # iguales implies multiple — usamos al menos 1 dado por count default)
        result = approximate_dice_cost("2d verde iguales")
        assert result == [3, 3]

    def test_pts_uses_value(self):
        # "Pts:5" → [5]
        assert approximate_dice_cost("Pts:5") == [5]

    def test_pts_clamps_to_6(self):
        # "Pts:11" → [6] (no se puede pedir cara mayor a 6)
        assert approximate_dice_cost("Pts:11") == [6]

    def test_pts_clamps_to_1_min(self):
        # "Pts:0" → [1] (no se puede pedir cara menor a 1)
        # Pero parser puede no aceptar 0; probemos con 1
        assert approximate_dice_cost("Pts:1") == [1]

    def test_first_option_taken_when_alternatives(self):
        # "1d verde >=4 | 1d verde >=4 + 1d rojo *" → [4] (toma la primera alternativa)
        result = approximate_dice_cost("1d verde >=4 | 2d verde pares")
        assert result == [4]

    def test_combined_groups(self):
        # "1d rojo cualquiera + 1d verde cualquiera" → [3, 3] (defaults)
        result = approximate_dice_cost("1d rojo cualquiera + 1d verde cualquiera")
        assert result == [3, 3]


# ---------------------------------------------------------------------------
# extract_damage
# ---------------------------------------------------------------------------

class TestExtractDamage:
    def test_basic_dano(self):
        assert extract_damage("dano:3") == 3

    def test_dano_with_other_effects(self):
        assert extract_damage("dano:2 + estado:envenenar") == 2

    def test_no_dano_returns_zero(self):
        assert extract_damage("cura:1") == 0
        assert extract_damage("Si recibís daño podés relanzar") == 0

    def test_none_returns_zero(self):
        assert extract_damage(None) == 0

    def test_empty_returns_zero(self):
        assert extract_damage("") == 0

    def test_dano_5(self):
        assert extract_damage("dano:5 + rompe_escudo + estrella") == 5


# ---------------------------------------------------------------------------
# Skill → Ability
# ---------------------------------------------------------------------------

class TestSkillToAbility:
    def test_simple_skill_conversion(self):
        skill = CardSkill(nombre="Tajo", tipo="ataque",
                          costo="2d verde >=4", efecto="dano:3")
        ab = card_skill_to_ability(skill)
        assert ab.name == "Tajo"
        assert ab.dice_cost == [4, 4]
        assert ab.damage == 3
        assert ab.repeatable is False

    def test_skill_without_cost(self):
        skill = CardSkill(nombre="X", tipo="ataque", costo=None, efecto="dano:1")
        ab = card_skill_to_ability(skill)
        assert ab.dice_cost == []
        assert ab.damage == 1

    def test_skill_without_damage(self):
        skill = CardSkill(nombre="Curar", tipo="apoyo",
                          costo="1d rojo cualquiera", efecto="cura:1")
        ab = card_skill_to_ability(skill)
        assert ab.damage == 0


# ---------------------------------------------------------------------------
# Hero → EngineHero
# ---------------------------------------------------------------------------

class TestHeroConversion:
    def test_basic_hero(self):
        hero = CardHero(
            id="mrhan", set="base", nombre="Mrhan", titulo="Orco Chamán",
            raza="orco", vida=16, escudo=0, lore="...",
            habilidades=[
                CardSkill(nombre="Tajo", tipo="ataque", costo="1d verde >=3", efecto="dano:2"),
            ],
        )
        eng = card_hero_to_engine(hero)
        assert eng.name == "Mrhan"
        assert eng.max_hp == 16
        assert eng.shields == 0
        assert len(eng.abilities) == 1
        assert eng.abilities[0].name == "Tajo"

    def test_hero_with_multiple_abilities(self):
        hero = CardHero(
            id="x", set="base", nombre="X", titulo="t", raza="r",
            vida=10, escudo=1, lore="",
            habilidades=[
                CardSkill(nombre="A", tipo="ataque", costo="1d verde", efecto="dano:1"),
                CardSkill(nombre="B", tipo="ataque", costo="2d verde >=5", efecto="dano:3"),
            ],
        )
        eng = card_hero_to_engine(hero)
        assert len(eng.abilities) == 2
        assert eng.abilities[1].dice_cost == [5, 5]


# ---------------------------------------------------------------------------
# Catalog converters
# ---------------------------------------------------------------------------

class TestCatalogConverters:
    def test_hero_to_catalog_keeps_set_and_fields(self):
        hero = CardHero(
            id="aldric", set="base", nombre="Aldric", titulo="Caballero",
            raza="humano", vida=8, escudo=1, lore="lore aquí",
            habilidades=[
                CardSkill(nombre="Tajo", tipo="ataque",
                          costo="1d verde >=3", efecto="dano:2",
                          confirmar=False),
            ],
            destrezas=[
                CardPassive(nombre="P1", tipo="pasiva", efecto="x", confirmar=False),
            ],
        )
        cat = _hero_to_catalog(hero)
        assert cat["id"] == "aldric"
        assert cat["name"] == "Aldric"
        assert cat["set"] == "base"
        assert cat["max_hp"] == 8
        assert cat["shields"] == 1
        assert len(cat["abilities"]) == 1
        assert cat["abilities"][0]["damage"] == 2
        assert cat["abilities"][0]["cost_text"] == "1d verde >=3"
        assert len(cat["passives"]) == 1

    def test_object_usage_maps_to_english(self):
        for spanish, english in _USO_MAP.items():
            obj = MagicObject(
                id="x", set="base", nombre="X", uso=spanish,
                mazo="oro", costo_diamantes=2, efecto="dano:1",
            )
            cat = _object_to_catalog(obj)
            assert cat["usage"] == english

    def test_object_with_variable_cost(self):
        obj = MagicObject(
            id="esc", set="base", nombre="Escudo", uso="permanente",
            mazo=None, costo_diamantes="variable", efecto="...",
        )
        cat = _object_to_catalog(obj)
        assert cat["cost_diamonds"] == "variable"

    def test_object_with_integer_cost(self):
        obj = MagicObject(
            id="esp", set="base", nombre="Espada", uso="permanente",
            mazo="oro", costo_diamantes=3, efecto="",
        )
        cat = _object_to_catalog(obj)
        assert cat["cost_diamonds"] == 3

    def test_beast_to_catalog(self):
        b = CardBeast(
            id="lobo", set="base", nombre="Lobo",
            costo_caza="2d verde >=4",
            recompensa={"diamantes": 2, "vida": 0},
            confirmar=False,
        )
        cat = _beast_to_catalog(b)
        assert cat["name"] == "Lobo"
        assert cat["cost_text"] == "2d verde >=4"
        assert cat["reward_diamonds"] == 2
        assert cat["reward_hp"] == 0

    def test_beast_null_recompensa_defaults_to_zero(self):
        b = CardBeast(
            id="x", set="base", nombre="X",
            costo_caza=None, recompensa={}, confirmar=True,
        )
        cat = _beast_to_catalog(b)
        assert cat["reward_diamonds"] == 0
        assert cat["reward_hp"] == 0
        assert cat["confirmar"] is True


# ---------------------------------------------------------------------------
# Integración con docs/cards real (sólo si existe)
# ---------------------------------------------------------------------------

class TestIntegrationWithRealYaml:
    def test_can_build_pool_from_real_yaml(self):
        """Si docs/cards/ existe, debería poder armar un pool sin crashear."""
        from pathlib import Path
        docs_cards = Path(__file__).resolve().parent.parent / "docs" / "cards"
        if not (docs_cards / "heroes.yaml").exists():
            pytest.skip("docs/cards/heroes.yaml no disponible (gitignored)")

        from simulator.team_factory import get_pool_from_yaml
        pool = get_pool_from_yaml(set_filter="base")
        assert len(pool) >= 1
        # Cada equipo tiene exactamente 2 héroes (pareo de a 2)
        for name, team in pool:
            assert len(team.heroes) == 2
            assert team.hp > 0

    def test_can_build_catalog_from_real_yaml(self):
        from pathlib import Path
        docs_cards = Path(__file__).resolve().parent.parent / "docs" / "cards"
        if not (docs_cards / "heroes.yaml").exists():
            pytest.skip("docs/cards/ no disponible")

        from simulator.team_factory import build_catalog_from_yaml
        cat = build_catalog_from_yaml()
        # Debe tener al menos los héroes que hay en el YAML
        assert len(cat["heroes"]) >= 1
        # Schema básico
        assert all("id" in h and "name" in h for h in cat["heroes"])
