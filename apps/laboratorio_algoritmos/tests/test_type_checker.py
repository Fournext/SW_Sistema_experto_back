import pytest
from apps.laboratorio_algoritmos.lenguaje.lexer import Lexer
from apps.laboratorio_algoritmos.lenguaje.parser import Parser
from apps.laboratorio_algoritmos.lenguaje.type_checker import TypeChecker
from apps.laboratorio_algoritmos.exceptions import TipoError


def verificar_codigo(codigo: str):
    tokens = Lexer(codigo).tokenizar()
    prog = Parser(tokens).parsear()
    tc = TypeChecker(prog)
    tc.verificar()
    return tc


def test_type_checker_ejemplo_canonico():
    codigo = """
    void FWCPasada(Regla[] R, BaseHechos BH) {
        for (int i = 0; i < R.length; i++) {
            if (!marcada(R[i])) {
                Hecho C = Disparar(R[i], BH);
                if (C != null) {
                    BH.add(C);
                    Marcar(R[i]);
                }
            }
        }
    }

    void FWC(Regla[] R, BaseHechos BH) {
        DesmarcarReglas(R);
        int pasada = 0;
        while (true) {
            pasada++;
            RegistrarPasada(pasada);
            int cantidadAntes = BH.length();
            FWCPasada(R, BH);
            if (cantidadAntes == BH.length()) {
                break;
            }
        }
        MostrarLosHechosDisparados(BH);
    }
    """
    tc = verificar_codigo(codigo)
    assert "FWC" in tc.funciones
    assert "FWCPasada" in tc.funciones


def test_type_checker_error_tipo_incompatible():
    codigo = """
    void test() {
        int x = "texto";
    }
    """
    with pytest.raises(TipoError) as exc_info:
        verificar_codigo(codigo)
    assert exc_info.value.codigo == "TIPO_INCOMPATIBLE"


def test_type_checker_error_condicion_no_booleana():
    codigo = """
    void test() {
        if (42) {
            int a = 1;
        }
    }
    """
    with pytest.raises(TipoError) as exc_info:
        verificar_codigo(codigo)
    assert exc_info.value.codigo == "CONDICION_NO_BOOLEANA"


def test_type_checker_error_variable_no_declarada():
    codigo = """
    void test() {
        x = 10;
    }
    """
    with pytest.raises(TipoError) as exc_info:
        verificar_codigo(codigo)
    assert exc_info.value.codigo == "VARIABLE_NO_DECLARADA"

