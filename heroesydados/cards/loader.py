from __future__ import annotations
from pathlib import Path
from typing import Optional
import yaml

from .models import Hero, Passive, Skill, Beast, MagicObject

def _find_repo_root(start: Path) -> Path:
    import subprocess
    try:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(start),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return Path(common).resolve().parent
    except Exception:
        for p in [start, *start.parents]:
            if (p / ".git").is_dir():
                return p
        return start


_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
_CARDS_DIR = _REPO_ROOT / "docs" / "cards"


def _cards_dir(override: Optional[Path]) -> Path:
    return Path(override) if override else _CARDS_DIR


def load_heroes(
    set_filter: Optional[str] = None,
    cards_dir: Optional[Path] = None,
) -> list[Hero]:
    path = _cards_dir(cards_dir) / "heroes.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    heroes = []
    for h in raw.get("heroes", []):
        if set_filter and h.get("set") != set_filter:
            continue
        destrezas = [
            Passive(
                nombre=d["nombre"],
                tipo=d.get("tipo", "pasiva"),
                efecto=d.get("efecto"),
                confirmar=bool(d.get("confirmar", False)),
            )
            for d in h.get("destrezas", [])
        ]
        habilidades = [
            Skill(
                nombre=s["nombre"],
                tipo=s.get("tipo", "ataque"),
                costo=s.get("costo"),
                efecto=s.get("efecto"),
                confirmar=bool(s.get("confirmar", False)),
            )
            for s in h.get("habilidades", [])
        ]
        heroes.append(
            Hero(
                id=h["id"],
                set=h["set"],
                nombre=h["nombre"],
                titulo=h["titulo"],
                raza=h["raza"],
                vida=int(h["vida"]),
                escudo=int(h.get("escudo", 0)),
                lore=h.get("lore", ""),
                destrezas=destrezas,
                habilidades=habilidades,
            )
        )
    return heroes


def load_beasts(
    set_filter: Optional[str] = None,
    cards_dir: Optional[Path] = None,
) -> list[Beast]:
    path = _cards_dir(cards_dir) / "beasts.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    beasts = []
    for b in raw.get("bestias", []):
        if set_filter and b.get("set") != set_filter:
            continue
        beasts.append(
            Beast(
                id=b["id"],
                set=b["set"],
                nombre=b["nombre"],
                costo_caza=b.get("costo_caza"),
                recompensa=b.get("recompensa") or {},
                confirmar=bool(b.get("confirmar", False)),
            )
        )
    return beasts


def load_objects(
    set_filter: Optional[str] = None,
    cards_dir: Optional[Path] = None,
) -> list[MagicObject]:
    path = _cards_dir(cards_dir) / "objects.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    objects = []
    for o in raw.get("objetos", []):
        if set_filter and o.get("set") != set_filter:
            continue
        objects.append(
            MagicObject(
                id=o["id"],
                set=o["set"],
                nombre=o["nombre"],
                uso=o["uso"],
                mazo=o.get("mazo"),
                costo_diamantes=o.get("costo_diamantes"),
                efecto=o.get("efecto"),
                confirmar=bool(o.get("confirmar", False)),
            )
        )
    return objects
