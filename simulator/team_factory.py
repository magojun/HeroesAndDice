"""
Bridge: cards loader (YAML) → engine teams (G10).

Convierte los modelos del cargador de cartas (heroesydados.cards.models)
a los modelos del motor de partida (engine.models) y produce dicts listos
para el catálogo del frontend.

Limitaciones conocidas:
- Los costos parseados (CostGroup con pares/iguales/Pts:N) se aproximan a
  list[int] de caras concretas. El motor actual no soporta restricciones
  combinatorias; las habilidades con esas costes pueden no activarse o
  activarse de forma simplificada. Documentado en HYD-62.
- `cura:N` y efectos complejos no se traducen a comportamiento del motor;
  solo se extrae `dano:N` para alimentar `Ability.damage`.
"""
from __future__ import annotations

import re
from typing import Optional

from engine.models import Ability, Hero as EngineHero, Team
from heroesydados.cards.loader import load_heroes, load_objects, load_beasts
from heroesydados.cards.models import Hero as CardHero, Skill as CardSkill
from heroesydados.skills.cost_parser import (
    parse_cost, COLOR_VERDE, COLOR_ROJO, COLOR_ANY,
    CONSTRAINT_PARES, CONSTRAINT_IMPARES, CONSTRAINT_IGUALES, CONSTRAINT_CONSECUTIVOS,
)


_RE_DANO = re.compile(r"dano:(\d+)", re.IGNORECASE)

# Mapeo de uso (español del YAML → inglés que espera el frontend)
_USO_MAP = {
    "permanente":    "permanent",
    "un_uso":        "single_use",
    "varios_usos":   "multi_use",
    "ciclar":        "cycle",
}


# ---------------------------------------------------------------------------
# Aproximación de costo: ParsedCost → list[int]
# ---------------------------------------------------------------------------

def approximate_dice_cost(cost_str: Optional[str]) -> list[int]:
    """
    Mejor-esfuerzo: convierte un string de costo del YAML a una list[int]
    de caras concretas que el motor pueda matchear.

    Reglas:
    - cost_str vacío / no parseable → []  (la habilidad no podrá activarse)
    - Si hay alternativas (A|B), toma la primera.
    - Para cada CostGroup:
        * Si tiene min_value (>=N), usa N.
        * Si tiene max_value (<=N), usa N.
        * Si tiene constraint pares  → usa 2.
        * Si tiene constraint impares → usa 1.
        * Si tiene constraint iguales → usa 3 (arbitrario).
        * Si tiene constraint consecutivos → usa 1.
        * Si es Pts:N → usa min(6, N) como cara única.
        * Si no tiene nada → usa 3 (valor medio).
      Y replica esa cara según `count`.
    """
    parsed = parse_cost(cost_str)
    if not parsed:
        return []

    option = parsed[0]
    out: list[int] = []
    for grp in option:
        if grp.is_pts and grp.pts_value is not None:
            out.append(min(6, max(1, grp.pts_value)))
            continue

        if grp.min_value is not None:
            val = grp.min_value
        elif grp.max_value is not None:
            val = grp.max_value
        elif grp.constraint == CONSTRAINT_PARES:
            val = 2
        elif grp.constraint == CONSTRAINT_IMPARES:
            val = 1
        elif grp.constraint == CONSTRAINT_IGUALES:
            val = 3
        elif grp.constraint == CONSTRAINT_CONSECUTIVOS:
            val = 1
        else:
            val = 3  # default

        count = grp.count if grp.count and grp.count > 0 else 1
        out.extend([val] * count)

    return out


def extract_damage(efecto: Optional[str]) -> int:
    """Extrae el daño base del string de efecto (busca 'dano:N')."""
    if not efecto:
        return 0
    m = _RE_DANO.search(efecto)
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# Bridge: CardHero → EngineHero
# ---------------------------------------------------------------------------

def card_skill_to_ability(skill: CardSkill) -> Ability:
    """Convierte una Skill del YAML a una Ability del motor."""
    return Ability(
        name=skill.nombre,
        dice_cost=approximate_dice_cost(skill.costo),
        damage=extract_damage(skill.efecto),
        repeatable=False,  # YAML no marca repetibles aún; conservador
    )


def card_hero_to_engine(hero: CardHero) -> EngineHero:
    """Convierte un Hero del YAML a un Hero del motor."""
    return EngineHero(
        name=hero.nombre,
        max_hp=hero.vida,
        shields=hero.escudo,
        abilities=[card_skill_to_ability(s) for s in hero.habilidades],
    )


def build_team_from_heroes(name: str, hero_ids: list[str],
                            set_filter: Optional[str] = None) -> tuple[str, Team]:
    """
    Arma un Team a partir de IDs de héroes del YAML.

    Args:
        name: nombre del equipo (para identificarlo en simulaciones).
        hero_ids: lista de IDs de heroes.yaml (típicamente 2 para el juego).
        set_filter: si se pasa, sólo carga héroes de ese set.

    Raises:
        ValueError si algún hero_id no existe en el YAML.
    """
    all_heroes = {h.id: h for h in load_heroes(set_filter=set_filter)}
    missing = [hid for hid in hero_ids if hid not in all_heroes]
    if missing:
        raise ValueError(f"Heroes no encontrados en heroes.yaml: {missing}")

    engine_heroes = [card_hero_to_engine(all_heroes[hid]) for hid in hero_ids]
    return name, Team(heroes=engine_heroes)


# ---------------------------------------------------------------------------
# Pool de referencia (reemplazo de sample_teams.get_reference_pool)
# ---------------------------------------------------------------------------

def get_pool_from_yaml(set_filter: Optional[str] = "base") -> list[tuple[str, Team]]:
    """
    Arma un pool de equipos de referencia a partir del YAML real.
    Agrupa los héroes de a 2 según el orden del YAML.

    Si hay impares (ej. 7 héroes), el último queda sin pareja y se omite
    con un warning.
    """
    heroes = load_heroes(set_filter=set_filter)
    if len(heroes) < 2:
        raise ValueError(
            f"Necesitás al menos 2 héroes en heroes.yaml (set={set_filter})"
        )

    pool: list[tuple[str, Team]] = []
    for i in range(0, len(heroes) - 1, 2):
        h1, h2 = heroes[i], heroes[i + 1]
        team_name = f"{h1.nombre} & {h2.nombre}"
        team = Team(heroes=[card_hero_to_engine(h1), card_hero_to_engine(h2)])
        pool.append((team_name, team))

    if len(heroes) % 2 == 1:
        print(f"[warn] {heroes[-1].nombre} quedó sin pareja (héroes impares)")

    return pool


# ---------------------------------------------------------------------------
# Bridge para el catálogo del frontend
# ---------------------------------------------------------------------------

def _ability_to_catalog(skill: CardSkill) -> dict:
    return {
        "name": skill.nombre,
        "cost_text": skill.costo or "",
        "damage": extract_damage(skill.efecto),
        "tipo": skill.tipo,
        "efecto": skill.efecto or "",
        "confirmar": bool(skill.confirmar),
    }


def _hero_to_catalog(hero: CardHero) -> dict:
    return {
        "id": hero.id,
        "name": hero.nombre,
        "titulo": hero.titulo,
        "raza": hero.raza,
        "set": hero.set,
        "max_hp": hero.vida,
        "shields": hero.escudo,
        "lore": hero.lore,
        "abilities": [_ability_to_catalog(s) for s in hero.habilidades],
        "passives": [
            {"name": p.nombre, "efecto": p.efecto or "", "confirmar": bool(p.confirmar)}
            for p in hero.destrezas
        ],
    }


def _object_to_catalog(obj) -> dict:
    cost = obj.costo_diamantes
    # Normalizar cost_diamonds: None/'variable' → None, número → int si se puede
    cost_diamonds: object = None
    if isinstance(cost, (int, float)):
        cost_diamonds = int(cost)
    elif isinstance(cost, str):
        cost_diamonds = cost  # 'variable' u otra cadena descriptiva
    return {
        "id": obj.id,
        "name": obj.nombre,
        "set": obj.set,
        "cost_diamonds": cost_diamonds,
        "usage": _USO_MAP.get(obj.uso, obj.uso),
        "mazo": obj.mazo,
        "damage_bonus": extract_damage(obj.efecto),
        "efecto": obj.efecto or "",
        "confirmar": bool(obj.confirmar),
    }


def _beast_to_catalog(beast) -> dict:
    rec = beast.recompensa or {}
    return {
        "id": beast.id,
        "name": beast.nombre,
        "set": beast.set,
        "cost_text": beast.costo_caza or "",
        "reward_diamonds": rec.get("diamantes") or 0,
        "reward_hp": rec.get("vida") or 0,
        "confirmar": bool(beast.confirmar),
    }


def build_catalog_from_yaml(set_filter: Optional[str] = None) -> dict:
    """
    Genera el dict de catálogo para el frontend usando datos reales del YAML.
    Si set_filter se pasa, filtra a un solo set.
    """
    return {
        "heroes": [_hero_to_catalog(h) for h in load_heroes(set_filter=set_filter)],
        "items":  [_object_to_catalog(o) for o in load_objects(set_filter=set_filter)],
        "beasts": [_beast_to_catalog(b) for b in load_beasts(set_filter=set_filter)],
    }
