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


def test_vm_ejecucion_ejercicio_7_consulta_previa():
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
            
            // Buscar la primera regla no marcada para consultar su premisa
            for (int k = 0; k < R.length; k++) {
                if (!marcada(R[k])) {
                    Variable[] varsPremisa = VariablesPremisa(R[k]);
                    if (varsPremisa.length > 0) {
                        Variable v = varsPremisa[0];
                        if (!Consultada(v) && !BH.contains(v)) {
                            Hecho resp = Preguntar("¿Cuál es el valor de " + v.nombre + "?", v);
                            if (resp != null) {
                                BH.add(resp);
                            }
                        }
                    }
                    break;
                }
            }
            
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

    # R1: IF Fiebre == Si THEN Infeccion = Si
    reglas_datos = {
        "r1": {
            "condiciones": [{"variable_nombre": "Fiebre", "operador": "==", "valor_esperado": "Si"}],
            "conclusion": {"variable_id": "v_inf", "variable_nombre": "Infeccion", "valor_resultante": "Si"}
        }
    }
    evaluador = EvaluadorReglasSnapshot(reglas_datos)

    r1 = ReglaRef(
        id="r1",
        nombre="R1",
        premisas=[{"variable": "Fiebre", "operador": "==", "valor": "Si"}]
    )
    arreglo_reglas = [r1]
    bh = BaseHechosValue()

    vm = VirtualMachine(compiled, evaluador_reglas=evaluador)
    vm.inicializar(bindings={"R": arreglo_reglas, "BH": bh}, entrada_principal="FWC")

    # Ejecutar hasta encontrar la consulta interactiva
    vm.ejecutar_hasta_pausa(max_pasos_visibles=50, max_instrucciones_lote=500)

    assert vm.estado.estado == "ESPERANDO_ENTRADA"
    assert vm.estado.pregunta_pendiente is not None
    assert vm.estado.pregunta_pendiente.variable_nombre == "Fiebre"
    assert "Fiebre" in vm.estado.pregunta_pendiente.texto

    # Responder a la pregunta
    id_preg = vm.estado.pregunta_pendiente.id_pregunta
    vm.resolver_pregunta(id_pregunta=id_preg, valor="Si")

    # Continuar la ejecución hasta el final
    while vm.estado.estado == "EJECUTANDO":
        vm.ejecutar_hasta_pausa(max_pasos_visibles=50, max_instrucciones_lote=500)

    assert vm.estado.estado == "FINALIZADA"
    assert bh.contains(VariableRef(id="v_fiebre", nombre="Fiebre"))
    assert bh.contains(VariableRef(id="v_inf", nombre="Infeccion"))
    assert bh.length() == 2
    assert "r1" in vm.estado.marcas_reglas


def test_vm_ejecucion_pizarron_marcado_variables():
    # Algoritmo idéntico a las fotos de pizarra del docente:
    # FWCPasada con marcar(V), marcada(V), getVarPremisa(), HechoNativo(V), Pregunta()
    # FWC con DesmarcarReglas(), DesmarcarVariables(), MarcarVariablesDeLaBH()
    codigo = """
    void FWCPasada(Regla[] R, BaseHechos BH) {
        for (int i = 0; i < R.length; i++) {
            if (!marcada(R[i])) {
                Hecho C = Disparar(R[i], BH);
                if (C != null) {
                    BH.add(C);
                    marcar(R[i]);
                } else {
                    Variable V = R[i].getVarPremisa();
                    if (!marcada(V) && HechoNativo(V)) {
                        Hecho H = Pregunta("Valor V", V);
                        marcar(V);
                        if (H != null) {
                            BH.add(H);
                        }
                    }
                }
            }
        }
    }

    void FWC(Regla[] R, BaseHechos BH) {
        DesmarcarReglas();
        DesmarcarVariables();
        MarcarVariablesDeLaBH();
        
        while (true) {
            int l = BH.length();
            FWCPasada(R, BH);
            if (l == BH.length()) {
                break;
            }
        }
    }
    """
    ast = Parser(Lexer(codigo).tokenizar()).parsear()
    TypeChecker(ast).verificar()
    compiled = Compiler(ast).compilar()

    reglas_datos = {
        "r1": {
            "id": "r1",
            "nombre": "R1",
            "condiciones": [{"variable_id": "v_tos", "variable_nombre": "Tos", "operador": "==", "valor_esperado": "Si", "es_nativa": True}],
            "conclusion": {"variable_id": "v_gripe", "variable_nombre": "Gripe", "valor_resultante": "Si"}
        }
    }
    evaluador = EvaluadorReglasSnapshot(reglas_datos)

    r1 = ReglaRef(
        id="r1",
        nombre="R1",
        premisas=[{"variable_id": "v_tos", "variable_nombre": "Tos", "operador": "==", "valor": "Si", "es_nativa": True}]
    )
    bh = BaseHechosValue()

    vm = VirtualMachine(compiled, evaluador_reglas=evaluador)
    vm.inicializar(bindings={"R": [r1], "BH": bh}, entrada_principal="FWC")

    # Ejecutar hasta que solicite la pregunta interactiva
    vm.ejecutar_hasta_pausa(max_pasos_visibles=50, max_instrucciones_lote=500)
    assert vm.estado.estado == "ESPERANDO_ENTRADA"
    assert vm.estado.pregunta_pendiente is not None
    assert vm.estado.pregunta_pendiente.variable_nombre == "Tos"

    # Resolver pregunta respondiendo "Si"
    id_preg = vm.estado.pregunta_pendiente.id_pregunta
    vm.resolver_pregunta(id_pregunta=id_preg, valor="Si")

    # Continuar la ejecución
    while vm.estado.estado == "EJECUTANDO":
        vm.ejecutar_hasta_pausa(max_pasos_visibles=50, max_instrucciones_lote=500)

    assert vm.estado.estado == "FINALIZADA"
    assert bh.contains(VariableRef(id="v_tos", nombre="Tos"))
    assert bh.contains(VariableRef(id="v_gripe", nombre="Gripe"))
    assert "r1" in vm.estado.marcas_reglas
    assert "v_tos" in vm.estado.variables_consultadas


