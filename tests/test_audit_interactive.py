"""Tests para las funciones de edición de audit_interactive."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from simulator.audit_interactive import (
    edit_inline_entry, edit_block_entry, _replace_value_in_line, _looks_like_number
)


# ---------------------------------------------------------------------------
# _looks_like_number
# ---------------------------------------------------------------------------

def test_number_detection():
    assert _looks_like_number("3")
    assert _looks_like_number("3.5")
    assert _looks_like_number("null")
    assert _looks_like_number("true")
    assert not _looks_like_number("hello")
    assert not _looks_like_number("oro")


# ---------------------------------------------------------------------------
# Inline edits (heroes.habilidades, objects)
# ---------------------------------------------------------------------------

class TestInlineEdit:
    def test_replace_costo_field(self):
        lines = ['      - { nombre: "Tajo", tipo: ataque, costo: "1d verde", efecto: "dano:1", confirmar: true }\n']
        edit_inline_entry(lines, 0, {"costo": "2d verde pares"}, validated=False)
        assert 'costo: "2d verde pares"' in lines[0]
        assert 'confirmar: true' in lines[0]  # no validado, no se toca

    def test_replace_and_validate(self):
        lines = ['      - { nombre: "Tajo", tipo: ataque, costo: "1d verde", efecto: "dano:1", confirmar: true }\n']
        edit_inline_entry(lines, 0,
                          {"costo": "2d verde", "efecto": "dano:3"},
                          validated=True)
        assert 'costo: "2d verde"' in lines[0]
        assert 'efecto: "dano:3"' in lines[0]
        assert 'confirmar' not in lines[0]

    def test_replace_numeric_field_no_quotes(self):
        lines = ['  - { id: x, costo_diamantes: null, mazo: null, uso: un_uso, confirmar: true }\n']
        edit_inline_entry(lines, 0,
                          {"costo_diamantes": "3", "mazo": "oro"},
                          validated=True)
        # número sin comillas
        assert "costo_diamantes: 3" in lines[0]
        # string con comillas
        assert 'mazo: "oro"' in lines[0]
        assert "confirmar" not in lines[0]

    def test_keep_other_fields_intact(self):
        original = '      - { nombre: "Disparo", tipo: ataque, costo: "1d", efecto: "x", confirmar: true }\n'
        lines = [original]
        edit_inline_entry(lines, 0, {"costo": "2d"}, validated=False)
        # Otros campos intactos
        assert 'nombre: "Disparo"' in lines[0]
        assert 'tipo: ataque' in lines[0]
        assert 'efecto: "x"' in lines[0]

    def test_skip_field_with_none(self):
        original = '  - { nombre: "X", costo: "1d", efecto: "y", confirmar: true }\n'
        lines = [original]
        edit_inline_entry(lines, 0, {"costo": None, "efecto": "nuevo"}, validated=False)
        assert 'costo: "1d"' in lines[0]  # no cambió
        assert 'efecto: "nuevo"' in lines[0]


# ---------------------------------------------------------------------------
# Block edits (heroes.destrezas, beasts)
# ---------------------------------------------------------------------------

class TestBlockEdit:
    def test_replace_efecto_in_destreza_block(self):
        lines = [
            '    destrezas:\n',
            '      - nombre: "La tierra protege"\n',
            '        tipo: pasiva\n',
            '        efecto: "viejo efecto"\n',
            '        confirmar: true\n',
            '    habilidades:\n',
        ]
        edit_block_entry(lines, 1, {"efecto": "nuevo efecto"}, validated=True)
        joined = "".join(lines)
        assert 'efecto: "nuevo efecto"' in joined
        assert "confirmar: true" not in joined
        # No tocó la siguiente sección
        assert "habilidades:" in joined

    def test_keep_validated_false_keeps_confirmar(self):
        lines = [
            '      - nombre: "X"\n',
            '        tipo: pasiva\n',
            '        efecto: "viejo"\n',
            '        confirmar: true\n',
        ]
        edit_block_entry(lines, 0, {"efecto": "nuevo"}, validated=False)
        joined = "".join(lines)
        assert "confirmar: true" in joined

    def test_replace_beast_nested_field(self):
        lines = [
            '  - id: lobo\n',
            '    set: base\n',
            '    nombre: "Lobo"\n',
            '    costo_caza: null\n',
            '    recompensa:\n',
            '      diamantes: null\n',
            '      vida: null\n',
            '    confirmar: true\n',
        ]
        edit_block_entry(lines, 2, {
            "costo_caza": "2d verde >=4",
            "recompensa.diamantes": "2",
            "recompensa.vida": "0",
        }, validated=True)
        joined = "".join(lines)
        assert 'costo_caza: "2d verde >=4"' in joined
        assert "diamantes: 2" in joined
        assert "vida: 0" in joined
        assert "confirmar: true" not in joined

    def test_preserves_comments_in_block(self):
        lines = [
            '  - id: x\n',
            '    nombre: "X"\n',
            '    costo_caza: null      # dados — PENDIENTE\n',
            '    confirmar: true\n',
        ]
        edit_block_entry(lines, 1, {"costo_caza": "3d"}, validated=False)
        # El comentario debería preservarse
        assert "# dados — PENDIENTE" in lines[2]
        assert 'costo_caza: "3d"' in lines[2]


# ---------------------------------------------------------------------------
# _replace_value_in_line
# ---------------------------------------------------------------------------

class TestReplaceValueInLine:
    def test_basic(self):
        result = _replace_value_in_line("        efecto: null\n", "dano:3")
        assert result == '        efecto: "dano:3"\n'

    def test_preserves_indent(self):
        result = _replace_value_in_line("            costo: viejo\n", "nuevo")
        assert result.startswith("            ")
        assert 'costo: "nuevo"' in result

    def test_preserves_comment(self):
        result = _replace_value_in_line("    diamantes: null   # PENDIENTE\n", "2")
        assert "diamantes: 2" in result
        assert "# PENDIENTE" in result

    def test_number_no_quotes(self):
        result = _replace_value_in_line("  vida: null\n", "5")
        assert "vida: 5" in result
        assert '"5"' not in result
