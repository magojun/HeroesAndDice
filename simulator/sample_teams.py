"""
Equipos y catálogo de muestra para la CLI.

Como docs/cards/ está gitignored (contiene el reglamento del juego),
estos equipos hardcodeados sirven para que `python -m simulator.cli`
funcione out-of-the-box sin necesidad de los YAMLs.
"""
from __future__ import annotations

from engine.models import Team, Hero, Ability, Item, ItemUsage, Beast, Deck


def team_alpha() -> tuple[str, Team]:
    """Equipo balanceado: daño medio, HP medio, defensa media."""
    h1 = Hero(name="Aldric", max_hp=8, shields=1, abilities=[
        Ability(name="Tajo", dice_cost=[3], damage=2),
        Ability(name="Doble corte", dice_cost=[3, 3], damage=4),
    ])
    h2 = Hero(name="Brenna", max_hp=7, shields=1, abilities=[
        Ability(name="Disparo", dice_cost=[5], damage=2),
    ])
    return "Alpha", Team(heroes=[h1, h2])


def team_beta() -> tuple[str, Team]:
    """Equipo agresivo: alto daño, poca defensa."""
    h1 = Hero(name="Korr", max_hp=6, shields=0, abilities=[
        Ability(name="Embate", dice_cost=[2], damage=3, repeatable=True),
        Ability(name="Furia", dice_cost=[6], damage=5),
    ])
    h2 = Hero(name="Vex", max_hp=6, shields=0, abilities=[
        Ability(name="Daga rápida", dice_cost=[1], damage=2),
    ])
    return "Beta", Team(heroes=[h1, h2])


def team_gamma() -> tuple[str, Team]:
    """Equipo tanque: alto HP, alta defensa, daño bajo."""
    h1 = Hero(name="Thoren", max_hp=12, shields=2, abilities=[
        Ability(name="Bloqueo", dice_cost=[5], damage=1),
    ])
    h2 = Hero(name="Mira", max_hp=10, shields=1, abilities=[
        Ability(name="Lanza", dice_cost=[4], damage=2),
    ])
    return "Gamma", Team(heroes=[h1, h2])


def team_delta() -> tuple[str, Team]:
    """Equipo control: daño bajo pero con habilidades versátiles."""
    h1 = Hero(name="Yala", max_hp=8, shields=1, abilities=[
        Ability(name="Hechizo", dice_cost=[3, 4], damage=3),
        Ability(name="Toque", dice_cost=[2], damage=1, repeatable=True),
    ])
    h2 = Hero(name="Idris", max_hp=8, shields=1, abilities=[
        Ability(name="Daño leve", dice_cost=[1], damage=1, repeatable=True),
    ])
    return "Delta", Team(heroes=[h1, h2])


REFERENCE_POOL = [team_alpha, team_beta, team_gamma, team_delta]


def get_reference_pool() -> list[tuple[str, Team]]:
    """Devuelve el pool completo de equipos de referencia."""
    return [factory() for factory in REFERENCE_POOL]


# ---------------------------------------------------------------------------
# Catálogo de muestra (G2 fallback cuando docs/cards no está disponible)
# ---------------------------------------------------------------------------

SAMPLE_CATALOG = {
    "heroes": [
        {
            "id": "aldric", "name": "Aldric", "set": "base",
            "max_hp": 8, "shields": 1,
            "abilities": [
                {"name": "Tajo",        "cost_text": "♦3",   "damage": 2},
                {"name": "Doble corte", "cost_text": "♦3 ♦3", "damage": 4},
            ],
        },
        {
            "id": "brenna", "name": "Brenna", "set": "base",
            "max_hp": 7, "shields": 1,
            "abilities": [{"name": "Disparo", "cost_text": "♦5", "damage": 2}],
        },
        {
            "id": "korr", "name": "Korr", "set": "base",
            "max_hp": 6, "shields": 0,
            "abilities": [
                {"name": "Embate", "cost_text": "♦2", "damage": 3, "repeatable": True},
                {"name": "Furia",  "cost_text": "♦6", "damage": 5},
            ],
        },
        {
            "id": "thoren", "name": "Thoren", "set": "base",
            "max_hp": 12, "shields": 2,
            "abilities": [{"name": "Bloqueo", "cost_text": "♦5", "damage": 1}],
        },
        {
            "id": "yala", "name": "Yala", "set": "base",
            "max_hp": 8, "shields": 1,
            "abilities": [
                {"name": "Hechizo", "cost_text": "♦3 ♦4", "damage": 3},
                {"name": "Toque",   "cost_text": "♦2",   "damage": 1, "repeatable": True},
            ],
        },
    ],
    "items": [
        {"id": "espada",  "name": "Espada",   "set": "base",
         "cost_diamonds": 2, "usage": "permanent",  "damage_bonus": 1},
        {"id": "pocion",  "name": "Poción",   "set": "base",
         "cost_diamonds": 1, "usage": "single_use", "damage_bonus": 2},
        {"id": "amuleto", "name": "Amuleto",  "set": "base",
         "cost_diamonds": 3, "usage": "multi_use",  "damage_bonus": 1},
    ],
    "beasts": [
        {"id": "lobo",   "name": "Lobo",   "set": "base",
         "cost_text": "♦2 ♦3", "reward_diamonds": 2, "reward_hp": 0},
        {"id": "oso",    "name": "Oso",    "set": "base",
         "cost_text": "♦4 ♦5", "reward_diamonds": 1, "reward_hp": 2},
        {"id": "dragón", "name": "Dragón", "set": "base",
         "cost_text": "♦5 ♦5 ♦6", "reward_diamonds": 4, "reward_hp": 0},
    ],
}
