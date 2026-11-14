from apps.laboratorio_algoritmos.lenguaje.lexer import Lexer
from apps.laboratorio_algoritmos.lenguaje.parser import Parser
from apps.laboratorio_algoritmos.lenguaje.type_checker import TypeChecker
from apps.laboratorio_algoritmos.lenguaje.compiler import Compiler


def test_compiler_ejemplo_canonico():
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
    tokens = Lexer(codigo).tokenizar()
    prog = Parser(tokens).parsear()
    tc = TypeChecker(prog)
    tc.verificar()

    compiler = Compiler(prog)
    compiled = compiler.compilar(entrada_principal="FWC")

    assert "FWC" in compiled.funciones
    assert "FWCPasada" in compiled.funciones
    assert len(compiled.funciones["FWC"].instrucciones) > 0
    assert len(compiled.funciones["FWCPasada"].instrucciones) > 0

    # Verificar que se puede serializar a dict
    datos = compiled.to_dict()
    assert datos["entrada_principal"] == "FWC"
    assert "FWC" in datos["funciones"]

