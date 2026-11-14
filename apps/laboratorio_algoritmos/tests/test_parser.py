import pytest
from apps.laboratorio_algoritmos.lenguaje.lexer import Lexer
from apps.laboratorio_algoritmos.lenguaje.parser import Parser
from apps.laboratorio_algoritmos.lenguaje.ast_nodes import (
    ProgramNode, FunctionDefNode, IfStmtNode, WhileStmtNode, ForStmtNode
)

def test_lexer_basico():
    codigo = 'int x = 42; double y = 3.14; boolean b = true; String s = "hola mundo";'
    lexer = Lexer(codigo)
    tokens = lexer.tokenizar()
    assert len(tokens) > 0
    assert tokens[0].lexema == "int"
    assert tokens[1].lexema == "x"
    assert tokens[2].lexema == "="
    assert tokens[3].valor == 42


def test_parser_funcion_simple():
    codigo = """
    void FWC(Regla[] R, BaseHechos BH) {
        int x = 0;
        while (true) {
            x++;
            if (x == 10) {
                break;
            }
        }
    }
    """
    lexer = Lexer(codigo)
    tokens = lexer.tokenizar()
    parser = Parser(tokens)
    prog = parser.parsear()

    assert isinstance(prog, ProgramNode)
    assert len(prog.funciones) == 1
    func = prog.funciones[0]
    assert func.nombre == "FWC"
    assert func.tipo_retorno.nombre_base == "void"
    assert len(func.parametros) == 2
    assert func.parametros[0].nombre == "R"
    assert func.parametros[0].tipo.es_arreglo is True
    assert func.parametros[1].nombre == "BH"
    assert func.parametros[1].tipo.nombre_base == "BaseHechos"


def test_parser_ejemplo_canonico():
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
    lexer = Lexer(codigo)
    tokens = lexer.tokenizar()
    parser = Parser(tokens)
    prog = parser.parsear()

    assert len(prog.funciones) == 2
    assert prog.funciones[0].nombre == "FWCPasada"
    assert prog.funciones[1].nombre == "FWC"

