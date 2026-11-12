"""
Pruebas unitarias para el AST Evaluator de premisas lógicas complejas.
"""
import pytest
from apps.inferencia.ast_evaluator import (
    compilar_expresion,
    evaluar_expresion_logica,
    BinaryOpNode,
    NotNode,
    AtomNode,
)


def test_evaluacion_atomica_simple():
    memoria = {"A": "b", "P": 15}
    cumple, det = evaluar_expresion_logica("A = b", memoria)
    assert cumple is True
    assert det["resultado"] is True

    cumple_falso, _ = evaluar_expresion_logica("A = c", memoria)
    assert cumple_falso is False


def test_expresion_or_simple():
    # IF (A=b AND B=0) OR P>10
    expr = "(A=b AND B=0) OR P>10"
    
    # Caso 1: A=b pero B!=0, pero P=15 (>10) -> Debe ser True por la rama derecha del OR
    memoria1 = {"A": "b", "B": 5, "P": 15}
    cumple1, _ = evaluar_expresion_logica(expr, memoria1)
    assert cumple1 is True

    # Caso 2: A=b y B=0, pero P=5 (<=10) -> Debe ser True por la rama izquierda del OR
    memoria2 = {"A": "b", "B": 0, "P": 5}
    cumple2, _ = evaluar_expresion_logica(expr, memoria2)
    assert cumple2 is True

    # Caso 3: A=c, B=5, P=5 -> Ambas ramas falsas -> Debe ser False
    memoria3 = {"A": "c", "B": 5, "P": 5}
    cumple3, _ = evaluar_expresion_logica(expr, memoria3)
    assert cumple3 is False


def test_expresion_anidada_doble_and_or():
    # IF (A=b AND B=0) OR (P>10 AND P<100)
    expr = "(A=b AND B=0) OR (P>10 AND P<100)"

    # P=50 está en rango (10, 100), rama derecha verdadera
    memoria1 = {"A": "otro", "B": 99, "P": 50}
    cumple1, _ = evaluar_expresion_logica(expr, memoria1)
    assert cumple1 is True

    # P=150 fuera de rango, rama derecha falsa; pero rama izquierda verdadera
    memoria2 = {"A": "b", "B": 0, "P": 150}
    cumple2, _ = evaluar_expresion_logica(expr, memoria2)
    assert cumple2 is True

    # Ambas falsas
    memoria3 = {"A": "otro", "B": 99, "P": 150}
    cumple3, _ = evaluar_expresion_logica(expr, memoria3)
    assert cumple3 is False


def test_conectores_en_espanol_y_simbolos():
    # (A=b Y B=0) O P>10
    expr_es = "(A=b Y B=0) O P>10"
    memoria = {"A": "b", "B": 0, "P": 5}
    cumple, _ = evaluar_expresion_logica(expr_es, memoria)
    assert cumple is True

    # Con símbolos: (A=b && B=0) || P>10
    expr_sym = "(A=b && B=0) || P>10"
    cumple_sym, _ = evaluar_expresion_logica(expr_sym, memoria)
    assert cumple_sym is True


def test_operador_not():
    expr = "NOT (A=b) AND P>10"
    memoria = {"A": "x", "P": 20}
    cumple, _ = evaluar_expresion_logica(expr, memoria)
    assert cumple is True

    memoria_falsa = {"A": "b", "P": 20}
    cumple_falsa, _ = evaluar_expresion_logica(expr, memoria_falsa)
    assert cumple_falsa is False


def test_variable_booleana_implicita():
    expr = "activo AND edad >= 18"
    memoria_si = {"activo": True, "edad": 20}
    cumple_si, _ = evaluar_expresion_logica(expr, memoria_si)
    assert cumple_si is True

    memoria_no = {"activo": False, "edad": 20}
    cumple_no, _ = evaluar_expresion_logica(expr, memoria_no)
    assert cumple_no is False


def test_insensibilidad_a_mayusculas_en_variables():
    expr = "temperatura > 37.5 AND estado = 'fiebre'"
    memoria = {"Temperatura": 38.2, "ESTADO": "fiebre"}
    cumple, _ = evaluar_expresion_logica(expr, memoria)
    assert cumple is True

