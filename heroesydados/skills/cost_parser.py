"""Parser de costos de habilidades según la simbología del reglamento (sección 6).

Gramática informal de un string de costo:
  cost      ::= option ("|" option)*
  option    ::= group ("+" group)*
  group     ::= pts_group | die_group | placeholder
  pts_group ::= "Pts:" INT
  die_group ::= [count] color [constraint] [value_bound]
  count     ::= INT "d" ["+"]          -- "Nd" o "Nd+"
  color     ::= "verde" | "rojo" | "cualquiera" | "*"  (ausencia → cualquiera)
  constraint::= "pares" | "impares" | "iguales" | "consecutivos"
  value_bound::= ">=" INT | "<=" INT

`confirmar: true` en la habilidad indica que el costo puede estar incompleto;
el parser tolera grupos vacíos / placeholders y los omite.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

COLOR_VERDE = "verde"
COLOR_ROJO = "rojo"
COLOR_ANY = "cualquiera"

CONSTRAINT_PARES = "pares"
CONSTRAINT_IMPARES = "impares"
CONSTRAINT_IGUALES = "iguales"
CONSTRAINT_CONSECUTIVOS = "consecutivos"


@dataclass
class CostGroup:
    """One atomic cost requirement (a group of dice of one color/constraint)."""

    color: str = COLOR_ANY           # 'verde' | 'rojo' | 'cualquiera'
    count: Optional[int] = None      # None = unspecified (any number)
    count_min: bool = False          # True when written as "Nd+" (at least N)
    constraint: Optional[str] = None # pares|impares|iguales|consecutivos
    min_value: Optional[int] = None  # >= N  (mayores: >=4)
    max_value: Optional[int] = None  # <= N  (menores: <=3)
    is_pts: bool = False             # Pts:N  (sum of any dice >= N)
    pts_value: Optional[int] = None


# A single spending option (groups connected by "+")
CostOption = list[CostGroup]

# Full parsed cost (list of alternatives separated by "|")
# Empty list means cost is null or unparseable (skill with confirmar:true).
ParsedCost = list[CostOption]


# ---------------------------------------------------------------------------
# Group-level parser
# ---------------------------------------------------------------------------

_RE_PTS = re.compile(r"^Pts:(\d+)$", re.IGNORECASE)
_RE_COUNT = re.compile(r"(\d+)d(\+)?")
_RE_GE = re.compile(r">=(\d+)")
_RE_LE = re.compile(r"<=(\d+)")
_RE_PLACEHOLDER = re.compile(r"^\(.*\)$")
_VAGUE_TOKENS = {"varios", "varios d", "dado", "dados", "verdes"}


def _parse_group(raw: str) -> Optional[CostGroup]:
    """Parse a single group token. Returns None for placeholders/vague text."""
    s = raw.strip()

    if not s or _RE_PLACEHOLDER.match(s):
        return None

    # Normalise: collapse multiple spaces
    s = re.sub(r"\s+", " ", s)

    # "varios d verde" / "varios d" / vague stubs
    words = set(s.lower().split())
    if words <= _VAGUE_TOKENS | {"d", "verde", "rojo", "cualquiera"}:
        # Only vague tokens; still try to extract color at minimum
        if not any(kw in s for kw in ("verde", "rojo", "cualquiera", "Pts", ">=", "<=")):
            return None  # truly unparseable

    # --- Pts group ---
    m = _RE_PTS.match(s)
    if m:
        return CostGroup(color=COLOR_ANY, is_pts=True, pts_value=int(m.group(1)))

    group = CostGroup()

    # --- Count (e.g. "3d", "2d+") ---
    m = _RE_COUNT.search(s)
    if m:
        group.count = int(m.group(1))
        group.count_min = m.group(2) == "+"

    # --- Color ---
    sl = s.lower()
    if "rojo" in sl:
        group.color = COLOR_ROJO
    elif "verde" in sl or "verdes" in sl:
        group.color = COLOR_VERDE
    # else: COLOR_ANY (dado multicolor / comodín)

    # --- Constraint ---
    # IMPORTANTE: chequear "impares" antes que "pares" (substring match)
    if "impares" in sl or "impar " in sl or sl.endswith("impar"):
        group.constraint = CONSTRAINT_IMPARES
    elif "pares" in sl:
        group.constraint = CONSTRAINT_PARES
    elif "iguales" in sl:
        group.constraint = CONSTRAINT_IGUALES
    elif "consecutivos" in sl or "consecutivo" in sl:
        group.constraint = CONSTRAINT_CONSECUTIVOS

    # --- Value bounds ---
    m = _RE_GE.search(s)
    if m:
        group.min_value = int(m.group(1))
    m = _RE_LE.search(s)
    if m:
        group.max_value = int(m.group(1))

    return group


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_cost(cost_str: Optional[str]) -> ParsedCost:
    """Parse a skill cost string to a list of CostOptions (alternatives).

    Returns an empty list when:
    - cost_str is None or empty (no cost / data pending confirmar:true).
    - The string cannot be meaningfully parsed.

    Each CostOption is a list of CostGroups that must ALL be satisfied (+).
    The skill fires if ANY option can be satisfied (|).
    """
    if not cost_str:
        return []

    parsed: ParsedCost = []

    for alt_raw in cost_str.split("|"):
        option: CostOption = []
        # Split on "+" only when surrounded by whitespace to avoid splitting "2d+"
        for grp_raw in re.split(r"\s+\+\s+", alt_raw):
            grp = _parse_group(grp_raw)
            if grp is not None:
                option.append(grp)
        if option:
            parsed.append(option)

    return parsed
