from apps.laboratorio_algoritmos.lenguaje.lexer import Lexer
from apps.laboratorio_algoritmos.lenguaje.parser import Parser
from apps.laboratorio_algoritmos.lenguaje.type_checker import TypeChecker
from apps.laboratorio_algoritmos.lenguaje.compiler import Compiler
from apps.laboratorio_algoritmos.runtime.values import (
    ReglaRef, VariableRef, HechoValor, BaseHechosValue
)
from apps.laboratorio_algoritmos.runtime.vm import VirtualMachine, EvaluadorReglasSnapshot


def test_vm_ejecucion_fwc_completa():
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

    # Snapshot de reglas:
    # R1: IF A == true THEN B = true
    # R2: IF B == true THEN C = true
    reglas_datos = {
        "r1": {
            "condiciones": [{"variable_nombre": "A", "operador": "==", "valor_esperado": "true"}],
            "conclusion": {"variable_id": "v_b", "variable_nombre": "B", "valor_resultante": "true"}
        },
        "r2": {
            "condiciones": [{"variable_nombre": "B", "operador": "==", "valor_esperado": "true"}],
            "conclusion": {"variable_id": "v_c", "variable_nombre": "C", "valor_resultante": "true"}
        }
    }
    evaluador = EvaluadorReglasSnapshot(reglas_datos)

    r1 = ReglaRef(id="r1", nombre="R1")
    r2 = ReglaRef(id="r2", nombre="R2")
    arreglo_reglas = [r1, r2]

    # Base de hechos inicial: A = true
    bh = BaseHechosValue()
    bh.add(HechoValor(id="h1", variable_id="v_a", variable_nombre="A", valor="true"))

    vm = VirtualMachine(compiled, evaluador_reglas=evaluador)
    vm.inicializar(bindings={"R": arreglo_reglas, "BH": bh}, entrada_principal="FWC")

    # Ejecutar hasta finalizar
    while vm.estado.estado == "EJECUTANDO":
        vm.ejecutar_hasta_pausa(max_pasos_visibles=50, max_instrucciones_lote=500)

    assert vm.estado.estado == "FINALIZADA"
    # Comprobar que la BH derivó B y C
    assert bh.contains(VariableRef(id="v_a", nombre="A"))
    assert bh.contains(VariableRef(id="v_b", nombre="B"))
    assert bh.contains(VariableRef(id="v_c", nombre="C"))
    assert bh.length() == 3

    # Comprobar que ambas reglas quedaron marcadas
    assert "r1" in vm.estado.marcas_reglas
    assert "r2" in vm.estado.marcas_reglas
    assert len(vm.estado.salidas_texto) > 0
    assert "Hechos derivados:" in vm.estado.salidas_texto[0]

