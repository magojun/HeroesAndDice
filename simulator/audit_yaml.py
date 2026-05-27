"""
Audit tool para los YAMLs de cartas (Epic E1 / E2).

Recorre docs/cards/*.yaml y reporta:
  - Toda entrada con `confirmar: true` (fields pendientes de validar contra la
    carta física).
  - Toda entrada con campos null/None obligatorios (costo_diamantes, costo_caza,
    etc.) que indica que está sin transcribir.
  - Conteo total para tener una métrica de progreso.

Uso:
    python -m simulator.audit_yaml [--file heroes.yaml] [--only-pending]

Pensado como worklist: copiás el output, lo pegás en un editor y vas
tachando lo que validás contra la foto/carta.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Forzar UTF-8 en stdout (Windows usa cp1252 por defecto)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import yaml
except ImportError:
    print("Falta PyYAML. Instalá con: pip install pyyaml")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = REPO_ROOT / "docs" / "cards"


def audit_heroes(path: Path) -> list[dict]:
    """Devuelve issues: lista de dicts con type, hero, ability, value, line."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    issues = []

    for hero in data.get("heroes", []):
        for ab in hero.get("habilidades", []):
            if ab.get("confirmar"):
                issues.append({
                    "category": "PENDIENTE",
                    "hero": hero["nombre"],
                    "field": f"habilidad «{ab['nombre']}»",
                    "current": f"costo={ab.get('costo')!r}, efecto={ab.get('efecto')!r}",
                    "line": _find_line(text, ab["nombre"]),
                })
        for d in hero.get("destrezas", []):
            if d.get("confirmar"):
                issues.append({
                    "category": "PENDIENTE",
                    "hero": hero["nombre"],
                    "field": f"destreza «{d['nombre']}»",
                    "current": f"efecto={d.get('efecto')!r}",
                    "line": _find_line(text, d["nombre"]),
                })
    return issues


def audit_objects(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    issues = []

    for obj in data.get("objetos", []):
        problems = []
        if obj.get("confirmar"):
            problems.append("confirmar:true")
        if obj.get("costo_diamantes") in (None, "variable") and obj.get("uso") != "permanente":
            problems.append("falta costo_diamantes")
        if obj.get("mazo") is None:
            problems.append("falta mazo (oro/plata/bronce)")

        if problems:
            issues.append({
                "category": "PENDIENTE" if obj.get("confirmar") else "FALTANTE",
                "hero": "—",
                "field": f"objeto «{obj['nombre']}»",
                "current": " · ".join(problems) + f" · uso={obj.get('uso')}",
                "line": _find_line(text, obj["nombre"]),
            })
    return issues


def audit_beasts(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    issues = []

    for beast in data.get("bestias", []):
        problems = []
        if beast.get("confirmar"):
            problems.append("confirmar:true")
        if beast.get("costo_caza") is None:
            problems.append("falta costo_caza")
        if not beast.get("recompensa"):
            problems.append("falta recompensa")

        if problems:
            issues.append({
                "category": "PENDIENTE" if beast.get("confirmar") else "FALTANTE",
                "hero": "—",
                "field": f"bestia «{beast['nombre']}»",
                "current": " · ".join(problems),
                "line": _find_line(text, beast["nombre"]),
            })
    return issues


def _find_line(text: str, needle: str) -> int:
    """Encuentra la primera línea donde aparece el nombre (1-indexed)."""
    for i, line in enumerate(text.split("\n"), start=1):
        if f'"{needle}"' in line or f"'{needle}'" in line:
            return i
    return 0


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit de YAMLs de cartas")
    parser.add_argument("--file", choices=["heroes", "objects", "beasts", "all"],
                        default="all", help="Qué YAML auditar (default all)")
    parser.add_argument("--cards-dir", type=str, default=str(CARDS_DIR),
                        help=f"Directorio de cartas (default {CARDS_DIR})")
    args = parser.parse_args(argv)

    cards_dir = Path(args.cards_dir)
    if not cards_dir.is_dir():
        print(f"[error] No existe el directorio {cards_dir}")
        return 1

    targets = []
    if args.file in ("heroes", "all"):
        targets.append(("heroes.yaml", audit_heroes))
    if args.file in ("objects", "all"):
        targets.append(("objects.yaml", audit_objects))
    if args.file in ("beasts", "all"):
        targets.append(("beasts.yaml", audit_beasts))

    total = 0
    for filename, auditor in targets:
        path = cards_dir / filename
        if not path.exists():
            print(f"[skip] {filename} no existe")
            continue

        issues = auditor(path)
        print(f"\n{'=' * 70}")
        print(f"  {filename}  —  {len(issues)} items a revisar")
        print(f"{'=' * 70}")

        if not issues:
            print("  [ok] sin pendientes")
            continue

        # Agrupar por héroe si aplica
        current_hero = None
        for issue in issues:
            if issue["hero"] != current_hero:
                current_hero = issue["hero"]
                if current_hero != "—":
                    print(f"\n  Héroe: {current_hero}")
                else:
                    print()

            line_str = f"L{issue['line']:>3}" if issue["line"] else "  L?"
            cat = issue["category"]
            print(f"    [{cat}] {line_str}  {issue['field']}")
            print(f"             {issue['current']}")

        total += len(issues)

    print(f"\n{'=' * 70}")
    print(f"  TOTAL: {total} items pendientes en {len(targets)} archivo(s)")
    print(f"{'=' * 70}")
    print(f"  Fotos de referencia: {cards_dir / 'img'}/")
    print(f"  Editá los YAMLs y volvé a correr `python -m simulator.audit_yaml`")
    print(f"  para ver el progreso.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
