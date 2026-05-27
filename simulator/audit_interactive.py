"""
Audit interactivo de YAMLs de cartas (E1/E2).

Walkthrough de cada item con `confirmar: true` o campos faltantes:
te muestra el estado actual, pedís los nuevos valores con prompts,
edita el YAML in-place preservando comentarios y formato.

Uso:
    python -m simulator.audit_interactive
    python -m simulator.audit_interactive --file heroes
    python -m simulator.audit_interactive --file objects
    python -m simulator.audit_interactive --file beasts

Controles dentro de cada item:
    Enter         mantener valor actual del campo
    s             saltar este item (volver luego)
    q             salir y guardar lo que ya editaste
    !             omitir validación final (mantiene confirmar:true)

Hace backup .bak antes de tocar nada. Guarda después de cada item validado,
así si crasheás no perdés todo.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# UTF-8 en Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

try:
    import yaml
except ImportError:
    print("Falta PyYAML. Instalá con: pip install pyyaml")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = REPO_ROOT / "docs" / "cards"

QUIT = object()       # señal de salida
SKIP = object()       # señal de saltar item


# ---------------------------------------------------------------------------
# Modelo de pendiente
# ---------------------------------------------------------------------------

class Pending:
    """Una entrada que necesita revisión."""

    def __init__(self, file, kind, name, line, fields, hero=None):
        self.file = file          # Path al .yaml
        self.kind = kind          # 'hero_skill' | 'hero_passive' | 'object' | 'beast'
        self.name = name          # nombre de la entrada
        self.line = line          # 1-indexed line donde aparece nombre
        self.fields = fields      # dict con valores actuales
        self.hero = hero          # para skills/passives, el héroe contenedor


# ---------------------------------------------------------------------------
# Scanner — detectar pendientes
# ---------------------------------------------------------------------------

def _find_line(text, needle):
    for i, line in enumerate(text.split("\n"), start=1):
        if f'"{needle}"' in line or f"'{needle}'" in line:
            return i
    return 0


def scan_heroes(path):
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    items = []
    for h in data.get("heroes", []):
        for ab in h.get("habilidades", []):
            if ab.get("confirmar"):
                items.append(Pending(
                    file=path, kind="hero_skill", name=ab["nombre"],
                    line=_find_line(text, ab["nombre"]),
                    fields={"costo": ab.get("costo"), "efecto": ab.get("efecto"),
                            "tipo": ab.get("tipo")},
                    hero=h["nombre"],
                ))
        for d in h.get("destrezas", []):
            if d.get("confirmar"):
                items.append(Pending(
                    file=path, kind="hero_passive", name=d["nombre"],
                    line=_find_line(text, d["nombre"]),
                    fields={"efecto": d.get("efecto"), "tipo": d.get("tipo")},
                    hero=h["nombre"],
                ))
    return items


def scan_objects(path):
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    items = []
    for o in data.get("objetos", []):
        needs = o.get("confirmar") or o.get("mazo") is None or (
            o.get("costo_diamantes") in (None, "variable") and o.get("uso") != "permanente"
        )
        if needs:
            items.append(Pending(
                file=path, kind="object", name=o["nombre"],
                line=_find_line(text, o["nombre"]),
                fields={
                    "costo_diamantes": o.get("costo_diamantes"),
                    "mazo": o.get("mazo"),
                    "uso": o.get("uso"),
                    "efecto": o.get("efecto"),
                },
            ))
    return items


def scan_beasts(path):
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    items = []
    for b in data.get("bestias", []):
        needs = b.get("confirmar") or b.get("costo_caza") is None or not b.get("recompensa")
        if needs:
            rec = b.get("recompensa") or {}
            items.append(Pending(
                file=path, kind="beast", name=b["nombre"],
                line=_find_line(text, b["nombre"]),
                fields={
                    "costo_caza": b.get("costo_caza"),
                    "recompensa_diamantes": rec.get("diamantes"),
                    "recompensa_vida": rec.get("vida"),
                },
            ))
    return items


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def banner(msg, char="─"):
    print()
    print(char * 72)
    print(f"  {msg}")
    print(char * 72)


def ask(label, current, allow_quit=True):
    """
    Prompt con valor actual. Retorna:
    - el nuevo valor (string)
    - QUIT si el usuario tipea 'q'
    - SKIP si el usuario tipea 's'
    - None si el usuario hace Enter (mantener actual)
    """
    show = current if current is not None else "(vacío)"
    prompt = f"  {label}\n    actual: {show}\n    nuevo : "
    try:
        raw = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return QUIT

    if allow_quit and raw.lower() == "q":
        return QUIT
    if raw.lower() == "s":
        return SKIP
    if raw == "":
        return None
    return raw


def ask_validate():
    """¿Validado? y → True, n → False, ! → mantener confirmar:true."""
    try:
        raw = input("\n  ¿Validado contra la carta física? (Y/n/!): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return raw not in ("n", "no", "!")


# ---------------------------------------------------------------------------
# Edición de archivos (preservando comentarios/formato)
# ---------------------------------------------------------------------------

def edit_inline_entry(lines, line_idx, new_values, validated):
    """
    Edita una línea con formato inline: { nombre: "...", costo: "...", ... }
    line_idx es 0-indexed. new_values es dict {field: new_value or None}.
    Si validated=True, quita ', confirmar: true' o ' confirmar: true,' de la línea.
    """
    line = lines[line_idx]
    for field, val in new_values.items():
        if val is None:
            continue
        pattern = rf'({re.escape(field)}\s*:\s*)(?:"[^"]*"|\'[^\']*\'|[^,}}\s]+)'
        # Formatear nuevo valor (string con comillas, número sin)
        if isinstance(val, str) and not _looks_like_number(val):
            new_str = f'"{val}"'
        else:
            new_str = str(val)
        # Lambda evita el problema de backrefs ambiguos cuando val empieza con dígito
        new_line, n = re.subn(pattern, lambda m: m.group(1) + new_str, line, count=1)
        if n > 0:
            line = new_line
        else:
            # El campo no existía; insertarlo antes del cierre `}`
            line = re.sub(r"(\s*})\s*$",
                          lambda m: f", {field}: {new_str}" + m.group(1),
                          line, count=1)

    if validated:
        # Eliminar confirmar:true del bloque inline
        # Casos: ", confirmar: true" o " confirmar: true,"
        line = re.sub(r",\s*confirmar\s*:\s*true", "", line)
        line = re.sub(r"confirmar\s*:\s*true\s*,?\s*", "", line)
        # Limpiar comas dobles que pudieran quedar
        line = re.sub(r",\s*,", ",", line)
        line = re.sub(r"{\s*,", "{", line)

    lines[line_idx] = line


def edit_block_entry(lines, name_line_idx, new_values, validated):
    """
    Edita un bloque YAML cuya entrada arranca con `- ` en alguna línea
    anterior o igual a name_line_idx. Busca campos hijos (mismo indent que
    el primer campo de la entrada) y los reemplaza. Soporta sub-campos
    notados como `parent.child` (ej: recompensa.diamantes).
    Si validated=True, elimina la línea `confirmar: true` del bloque.
    """
    # 1) Caminar hacia atrás para encontrar el `- ` que abre la entrada
    entry_start = name_line_idx
    while entry_start >= 0:
        s = lines[entry_start].lstrip()
        if s.startswith("- "):
            break
        entry_start -= 1
    if entry_start < 0:
        return  # no se encontró el comienzo del bloque

    # Indent del guión (el `-`) y de los hijos (campos a la altura del `- `)
    dash_line = lines[entry_start]
    dash_indent = len(dash_line) - len(dash_line.lstrip())
    child_indent = dash_indent + 2

    # 2) Encontrar el final del bloque (siguiente línea con indent <= dash_indent)
    end = entry_start + 1
    while end < len(lines):
        ln = lines[end]
        if ln.strip() == "":
            end += 1
            continue
        cur_indent = len(ln) - len(ln.lstrip())
        if cur_indent <= dash_indent:
            break
        end += 1

    # Helper: ¿esta línea está en `indent` y tiene el campo `name:`?
    def matches(line, indent, name):
        return re.match(rf"^[ ]{{{indent}}}{re.escape(name)}\s*:", line) is not None

    # La primera línea del bloque (la del `- `) también es "hija" lógicamente:
    # ej. `  - id: lobo` — `id` está justo después del `- `.
    # Lo tratamos como child_indent + offset = dash_indent + 2 = child_indent.
    # Pero `id` está físicamente en dash_indent + 2 (después del "- ").
    # Las líneas SIGUIENTES están físicamente en child_indent. OK.

    # 3) Reemplazar cada campo
    for field, val in new_values.items():
        if val is None:
            continue

        if "." in field:
            top, sub = field.split(".", 1)
            # Buscar la línea del top entre [entry_start+1, end)
            for i in range(entry_start + 1, end):
                if matches(lines[i], child_indent, top):
                    sub_indent = child_indent + 2
                    for j in range(i + 1, end):
                        if matches(lines[j], sub_indent, sub):
                            lines[j] = _replace_value_in_line(lines[j], val)
                            break
                    break
        else:
            # Buscar entre entry_start..end (inclusive del primer renglón con `- `)
            for i in range(entry_start, end):
                if matches(lines[i], child_indent, field):
                    lines[i] = _replace_value_in_line(lines[i], val)
                    break

    if validated:
        for i in range(entry_start + 1, end):
            if matches(lines[i], child_indent, "confirmar"):
                lines[i] = None
                break

    lines[:] = [ln for ln in lines if ln is not None]


def _replace_value_in_line(line, new_val):
    """Reemplaza el valor en una línea YAML `  campo: valor` preservando indent y campo."""
    if isinstance(new_val, str) and not _looks_like_number(new_val):
        new_str = f'"{new_val}"'
    else:
        new_str = str(new_val)
    # Preservar todo hasta `:` inclusive, y reemplazar el resto (incluyendo comentarios)
    m = re.match(r"^(\s*[^:]+:\s*)(.*?)(\s*#.*)?$", line.rstrip("\n"))
    if not m:
        return line
    prefix, _old, comment = m.group(1), m.group(2), (m.group(3) or "")
    return f"{prefix}{new_str}{comment}\n"


def _looks_like_number(s):
    if s in ("null", "true", "false"):
        return True
    try:
        float(s)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Walkthrough por tipo
# ---------------------------------------------------------------------------

def handle_hero_skill(item, lines):
    banner(f"HÉROE: {item.hero}  ·  HABILIDAD: «{item.name}»  (línea {item.line})")
    print(f"  tipo:   {item.fields['tipo']}\n")

    new_costo  = ask("Costo (ej: '2d verde pares + 1d rojo *')", item.fields["costo"])
    if new_costo is QUIT: return QUIT
    if new_costo is SKIP: return SKIP

    new_efecto = ask("Efecto (ej: 'dano:3 + estado:envenenar')",  item.fields["efecto"])
    if new_efecto is QUIT: return QUIT
    if new_efecto is SKIP: return SKIP

    validated = ask_validate()
    edit_inline_entry(lines, item.line - 1,
                      {"costo": new_costo, "efecto": new_efecto}, validated)
    return True


def handle_hero_passive(item, lines):
    banner(f"HÉROE: {item.hero}  ·  DESTREZA: «{item.name}»  (línea {item.line})")
    print(f"  tipo:   {item.fields['tipo']}\n")

    new_efecto = ask("Efecto", item.fields["efecto"])
    if new_efecto is QUIT: return QUIT
    if new_efecto is SKIP: return SKIP

    validated = ask_validate()
    edit_block_entry(lines, item.line - 1,
                     {"efecto": new_efecto}, validated)
    return True


def handle_object(item, lines):
    banner(f"OBJETO: «{item.name}»  (línea {item.line})")
    print(f"  uso:    {item.fields['uso']}\n")

    new_costo = ask("Costo en diamantes (número o 'variable')",
                    item.fields["costo_diamantes"])
    if new_costo is QUIT: return QUIT
    if new_costo is SKIP: return SKIP

    new_mazo  = ask("Mazo (oro / plata / bronce)", item.fields["mazo"])
    if new_mazo is QUIT: return QUIT
    if new_mazo is SKIP: return SKIP

    new_efecto = ask("Efecto", item.fields["efecto"])
    if new_efecto is QUIT: return QUIT
    if new_efecto is SKIP: return SKIP

    validated = ask_validate()
    edit_inline_entry(lines, item.line - 1, {
        "costo_diamantes": new_costo,
        "mazo": new_mazo,
        "efecto": new_efecto,
    }, validated)
    return True


def handle_beast(item, lines):
    banner(f"BESTIA: «{item.name}»  (línea {item.line})")

    new_costo = ask("Costo de caza (ej: '2d verde >=4')",
                    item.fields["costo_caza"])
    if new_costo is QUIT: return QUIT
    if new_costo is SKIP: return SKIP

    new_diam  = ask("Recompensa: diamantes",
                    item.fields["recompensa_diamantes"])
    if new_diam is QUIT: return QUIT
    if new_diam is SKIP: return SKIP

    new_vida  = ask("Recompensa: vida",
                    item.fields["recompensa_vida"])
    if new_vida is QUIT: return QUIT
    if new_vida is SKIP: return SKIP

    validated = ask_validate()
    edit_block_entry(lines, item.line - 1, {
        "costo_caza": new_costo,
        "recompensa.diamantes": new_diam,
        "recompensa.vida": new_vida,
    }, validated)
    return True


HANDLERS = {
    "hero_skill":   handle_hero_skill,
    "hero_passive": handle_hero_passive,
    "object":       handle_object,
    "beast":        handle_beast,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit interactivo de YAMLs")
    parser.add_argument("--file", choices=["heroes", "objects", "beasts", "all"],
                        default="all")
    parser.add_argument("--cards-dir", type=str, default=str(CARDS_DIR))
    parser.add_argument("--no-backup", action="store_true",
                        help="No crear archivo .bak antes de editar")
    args = parser.parse_args(argv)

    cards_dir = Path(args.cards_dir)
    if not cards_dir.is_dir():
        print(f"[error] No existe {cards_dir}")
        return 1

    plan = []
    if args.file in ("heroes", "all"):
        plan.append((cards_dir / "heroes.yaml", scan_heroes))
    if args.file in ("objects", "all"):
        plan.append((cards_dir / "objects.yaml", scan_objects))
    if args.file in ("beasts", "all"):
        plan.append((cards_dir / "beasts.yaml", scan_beasts))

    print()
    print("═" * 72)
    print("  AUDIT INTERACTIVO — Heroes y Dados")
    print("═" * 72)
    print("  En cada item: Enter mantiene valor · 's' salta · 'q' guarda y sale")
    print("  Al final preguntará si validaste contra la carta (Y/n/!)")
    print()

    total_done = 0
    total_skipped = 0

    for path, scanner in plan:
        if not path.exists():
            print(f"[skip] {path.name} no existe")
            continue

        items = scanner(path)
        if not items:
            print(f"[ok] {path.name}: sin pendientes")
            continue

        if not args.no_backup:
            shutil.copy(path, path.with_suffix(path.suffix + ".bak"))
            print(f"[backup] {path.name}.bak creado")

        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        # Re-escanear sobre la copia en memoria mientras editamos (las líneas pueden moverse)

        for idx, item in enumerate(items, start=1):
            print(f"\n[{idx}/{len(items)}] {path.name}")
            # Re-buscar la línea por si el contenido se desplazó
            current_text = "".join(lines)
            item.line = _find_line(current_text, item.name) or item.line

            handler = HANDLERS[item.kind]
            result = handler(item, lines)
            if result is QUIT:
                path.write_text("".join(lines), encoding="utf-8")
                print(f"\n[guardado] {path.name}")
                print(f"  hechos: {total_done}  ·  saltados: {total_skipped}  ·  quedan: {len(items) - idx}")
                return 0
            if result is SKIP:
                total_skipped += 1
                continue
            total_done += 1
            # Guardar tras cada cambio aceptado (anti-crash)
            path.write_text("".join(lines), encoding="utf-8")
            print(f"  [guardado] {path.name}")

        path.write_text("".join(lines), encoding="utf-8")

    print()
    print("═" * 72)
    print(f"  FIN — {total_done} items editados · {total_skipped} saltados")
    print(f"  Verificá con: python -m simulator.audit_yaml")
    print("═" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
