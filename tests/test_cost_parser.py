import pytest
from heroesydados.skills.cost_parser import (
    parse_cost, CostGroup,
    COLOR_VERDE, COLOR_ROJO, COLOR_ANY,
    CONSTRAINT_PARES, CONSTRAINT_IMPARES, CONSTRAINT_IGUALES, CONSTRAINT_CONSECUTIVOS,
)


# --- Null / empty costs ---

def test_null_cost_returns_empty():
    assert parse_cost(None) == []

def test_empty_string_returns_empty():
    assert parse_cost("") == []


# --- Pts costs ---

def test_pts_cost():
    result = parse_cost("Pts:11")
    assert len(result) == 1
    assert result[0][0].is_pts is True
    assert result[0][0].pts_value == 11

def test_pts_cost_5():
    result = parse_cost("Pts:5")
    assert result[0][0].pts_value == 5


# --- Simple die costs ---

def test_1d_verde_ge4():
    result = parse_cost("1d verde >=4")
    g = result[0][0]
    assert g.color == COLOR_VERDE
    assert g.count == 1
    assert g.min_value == 4

def test_1d_rojo_cualquiera():
    result = parse_cost("1d rojo cualquiera")
    g = result[0][0]
    assert g.color == COLOR_ROJO
    assert g.count == 1
    assert g.constraint is None
    assert g.min_value is None

def test_3d_verde_pares():
    result = parse_cost("3d verde pares")
    g = result[0][0]
    assert g.color == COLOR_VERDE
    assert g.count == 3
    assert g.constraint == CONSTRAINT_PARES

def test_4d_verde_iguales():
    result = parse_cost("4d verde iguales")
    g = result[0][0]
    assert g.count == 4
    assert g.constraint == CONSTRAINT_IGUALES

def test_3d_verde_le3():
    result = parse_cost("3d verde <=3")
    g = result[0][0]
    assert g.color == COLOR_VERDE
    assert g.count == 3
    assert g.max_value == 3

def test_4d_verde_ge4():
    result = parse_cost("4d verde >=4")
    g = result[0][0]
    assert g.count == 4
    assert g.min_value == 4

def test_count_min_syntax():
    result = parse_cost("2d+ verde iguales")
    g = result[0][0]
    assert g.count == 2
    assert g.count_min is True
    assert g.constraint == CONSTRAINT_IGUALES


# --- Compound costs ("+") ---

def test_compound_rojo_plus_verde():
    result = parse_cost("1d rojo cualquiera + 1d verde cualquiera")
    assert len(result) == 1
    option = result[0]
    assert len(option) == 2
    assert option[0].color == COLOR_ROJO
    assert option[1].color == COLOR_VERDE

def test_compound_verde_impar_plus_rojo():
    result = parse_cost("1d verde impar + 1d rojo *")
    option = result[0]
    assert option[0].constraint == CONSTRAINT_IMPARES
    assert option[1].color == COLOR_ROJO

def test_compound_consecutivos_plus_iguales():
    result = parse_cost("verde consecutivos + verde iguales")
    option = result[0]
    assert option[0].constraint == CONSTRAINT_CONSECUTIVOS
    assert option[1].constraint == CONSTRAINT_IGUALES


# --- Alternative costs ("|") ---

def test_alternatives_ge4_or_ge4_plus_rojo():
    result = parse_cost("1d verde >=4 | 1d verde >=4 + 1d rojo *")
    assert len(result) == 2
    assert len(result[0]) == 1
    assert len(result[1]) == 2

def test_alternatives_verde_consecutivos_or_iguales():
    result = parse_cost("verde consecutivos | verde iguales")
    assert len(result) == 2
    assert result[0][0].constraint == CONSTRAINT_CONSECUTIVOS
    assert result[1][0].constraint == CONSTRAINT_IGUALES

def test_alternatives_3d_or_verde_iguales():
    result = parse_cost("3d verde | verde iguales")
    assert len(result) == 2
    assert result[0][0].count == 3
    assert result[1][0].constraint == CONSTRAINT_IGUALES


# --- Placeholder / confirmar tolerence ---

def test_placeholder_group_ignored():
    result = parse_cost("3d verde + (a confirmar)")
    assert len(result) == 1
    assert len(result[0]) == 1  # placeholder group dropped
    assert result[0][0].count == 3

def test_dados_verde_without_count():
    result = parse_cost("dados verde <=3")
    g = result[0][0]
    assert g.color == COLOR_VERDE
    assert g.count is None
    assert g.max_value == 3
