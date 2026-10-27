"""
Pruebas unitarias puras del Motor de Inferencia por Encadenamiento hacia Adelante.
NO dependen de la base de datos ni de Django.
"""
import pytest
from uuid import uuid4

from apps.base_conocimiento.entities import Condicion, Conclusion, Hecho, Regla
from apps.inferencia.conflict_resolution import ResolucionPorPrioridad
from apps.inferencia.engine import MotorInferencia
from apps.inferencia.exceptions import LimiteIteracionesAlcanzado
from compartido.constantes.enums import TipoDato, OperadorCondicion, EstadoReglaInferencia


def test_caso_1_inferencia_simple():
    """
    Caso 1:
    Hecho A = true
    R1: SI A = true -> B = true
    Resultado esperado: B = true
    """
    id_hecho_a = uuid4()
    id_hecho_b = uuid4()

    hecho_a = Hecho(id=id_hecho_a, nombre="A", valor="true", tipo_dato=TipoDato.BOOLEANO, es_inicial=True)
    hecho_b = Hecho(id=id_hecho_b, nombre="B", valor=None, tipo_dato=TipoDato.BOOLEANO, es_inicial=False)

    regla_1 = Regla(
        id=uuid4(),
        nombre="R1",
        prioridad=1,
        activa=True,
        condiciones=[
            Condicion(hecho_id=id_hecho_a, operador=OperadorCondicion.IGUAL, valor_esperado="true")
        ],
        conclusiones=[
            Conclusion(hecho_resultante_id=id_hecho_b, valor_resultante="true")
        ],
    )

    motor = MotorInferencia()
    resultado = motor.ejecutar(
        hechos_iniciales=[hecho_a, hecho_b],
        reglas=[regla_1],
    )

    # Verificaciones
    assert resultado.conclusion_final == "true"
    nombres_generados = [h["nombre"] for h in resultado.hechos_generados]
    assert "B" in nombres_generados
    valores_generados = {h["nombre"]: h["valor"] for h in resultado.hechos_generados}
    assert valores_generados["B"] == "true"


def test_caso_2_encadenamiento_en_cascada():
    """
    Caso 2:
    A = true
    R1: SI A = true -> B = true
    R2: SI B = true -> C = true
    Resultado esperado:
    B = true
    C = true
    """
    id_a = uuid4()
    id_b = uuid4()
    id_c = uuid4()

    hecho_a = Hecho(id=id_a, nombre="A", valor="true", tipo_dato=TipoDato.BOOLEANO, es_inicial=True)
    hecho_b = Hecho(id=id_b, nombre="B", valor=None, tipo_dato=TipoDato.BOOLEANO, es_inicial=False)
    hecho_c = Hecho(id=id_c, nombre="C", valor=None, tipo_dato=TipoDato.BOOLEANO, es_inicial=False)

    regla_1 = Regla(
        id=uuid4(),
        nombre="R1",
        prioridad=5,
        activa=True,
        condiciones=[Condicion(hecho_id=id_a, operador=OperadorCondicion.IGUAL, valor_esperado="true")],
        conclusiones=[Conclusion(hecho_resultante_id=id_b, valor_resultante="true")],
    )

    regla_2 = Regla(
        id=uuid4(),
        nombre="R2",
        prioridad=5,
        activa=True,
        condiciones=[Condicion(hecho_id=id_b, operador=OperadorCondicion.IGUAL, valor_esperado="true")],
        conclusiones=[Conclusion(hecho_resultante_id=id_c, valor_resultante="true")],
    )

    motor = MotorInferencia()
    resultado = motor.ejecutar(
        hechos_iniciales=[hecho_a, hecho_b, hecho_c],
        reglas=[regla_1, regla_2],
    )

    nombres_generados = [h["nombre"] for h in resultado.hechos_generados]
    assert "B" in nombres_generados
    assert "C" in nombres_generados
    assert resultado.conclusion_final == "true"


def test_caso_3_resolucion_por_prioridad():
    """
    Caso 3:
    Reglas con distinta prioridad.
    Debe ejecutar primero la de mayor prioridad.
    """
    id_inicio = uuid4()
    id_dest = uuid4()

    hecho_inicio = Hecho(id=id_inicio, nombre="X", valor="10", tipo_dato=TipoDato.ENTERO)
    hecho_dest = Hecho(id=id_dest, nombre="Y", valor=None, tipo_dato=TipoDato.TEXTO)

    # R_Baja: prioridad 10
    regla_baja = Regla(
        id=uuid4(),
        nombre="ReglaBaja",
        prioridad=10,
        activa=True,
        condiciones=[Condicion(hecho_id=id_inicio, operador=OperadorCondicion.MAYOR, valor_esperado="5")],
        conclusiones=[Conclusion(hecho_resultante_id=id_dest, valor_resultante="Baja")],
    )

    # R_Alta: prioridad 20
    regla_alta = Regla(
        id=uuid4(),
        nombre="ReglaAlta",
        prioridad=20,
        activa=True,
        condiciones=[Condicion(hecho_id=id_inicio, operador=OperadorCondicion.MAYOR, valor_esperado="5")],
        conclusiones=[Conclusion(hecho_resultante_id=id_dest, valor_resultante="Alta")],
    )

    motor = MotorInferencia(estrategia_resolucion=ResolucionPorPrioridad())
    resultado = motor.ejecutar(
        hechos_iniciales=[hecho_inicio, hecho_dest],
        reglas=[regla_baja, regla_alta],
    )

    # Buscar la primera regla ejecutada en la traza
    reglas_ejecutadas = [
        t for t in resultado.reglas_evaluadas
        if t.estado == EstadoReglaInferencia.EJECUTADA
    ]
    assert len(reglas_ejecutadas) >= 1
    assert reglas_ejecutadas[0].regla_nombre == "ReglaAlta"


def test_caso_4_regla_no_cumple_queda_rechazada():
    """
    Caso 4:
    Regla no cumple condición -> Debe quedar registrada como RECHAZADA.
    """
    id_hecho = uuid4()
    hecho = Hecho(id=id_hecho, nombre="edad", valor="15", tipo_dato=TipoDato.ENTERO)

    regla = Regla(
        id=uuid4(),
        nombre="R_MayorEdad",
        prioridad=1,
        activa=True,
        condiciones=[Condicion(hecho_id=id_hecho, operador=OperadorCondicion.MAYOR_IGUAL, valor_esperado="18")],
        conclusiones=[Conclusion(hecho_resultante_id=uuid4(), valor_resultante="Adulto")],
    )

    motor = MotorInferencia()
    resultado = motor.ejecutar(
        hechos_iniciales=[hecho],
        reglas=[regla],
    )

    trazas_rechazadas = [t for t in resultado.reglas_evaluadas if t.estado == EstadoReglaInferencia.RECHAZADA]
    assert len(trazas_rechazadas) == 1
    assert trazas_rechazadas[0].regla_nombre == "R_MayorEdad"
    assert trazas_rechazadas[0].condiciones_cumplidas is False
    assert len(resultado.hechos_generados) == 0


def test_caso_5_regla_cumple_queda_activada_y_ejecutada():
    """
    Caso 5:
    Regla cumple condición -> Debe quedar registrada como ACTIVADA y EJECUTADA.
    """
    id_h = uuid4()
    id_res = uuid4()
    hecho = Hecho(id=id_h, nombre="temperatura", valor="38.5", tipo_dato=TipoDato.DECIMAL)
    hecho_res = Hecho(id=id_res, nombre="diagnostico", valor=None, tipo_dato=TipoDato.TEXTO)

    regla = Regla(
        id=uuid4(),
        nombre="R_Fiebre",
        prioridad=5,
        activa=True,
        condiciones=[Condicion(hecho_id=id_h, operador=OperadorCondicion.MAYOR, valor_esperado="37.5")],
        conclusiones=[Conclusion(hecho_resultante_id=id_res, valor_resultante="Fiebre")],
    )

    motor = MotorInferencia()
    resultado = motor.ejecutar(
        hechos_iniciales=[hecho, hecho_res],
        reglas=[regla],
    )

    trazas_activadas = [t for t in resultado.reglas_evaluadas if t.estado == EstadoReglaInferencia.ACTIVADA]
    trazas_ejecutadas = [t for t in resultado.reglas_evaluadas if t.estado == EstadoReglaInferencia.EJECUTADA]

    assert len(trazas_activadas) == 1
    assert len(trazas_ejecutadas) == 1
    assert trazas_ejecutadas[0].regla_nombre == "R_Fiebre"
    assert resultado.conclusion_final == "Fiebre"


def test_caso_6_detectar_limite_maximo_iteraciones():
    """
    Caso 6:
    Detectar límite máximo de iteraciones y lanzar la excepción LimiteIteracionesAlcanzado.
    """
    # Simulamos un motor configurado con max_iteraciones=0 para forzar el límite inmediato
    hecho = Hecho(id=uuid4(), nombre="A", valor="true", tipo_dato=TipoDato.BOOLEANO)
    regla = Regla(
        id=uuid4(),
        nombre="R1",
        prioridad=1,
        activa=True,
        condiciones=[Condicion(hecho_id=hecho.id, operador=OperadorCondicion.IGUAL, valor_esperado="true")],
        conclusiones=[Conclusion(hecho_resultante_id=hecho.id, valor_resultante="true")],
    )

    motor = MotorInferencia(max_iteraciones=0)
    with pytest.raises(LimiteIteracionesAlcanzado):
        motor.ejecutar(hechos_iniciales=[hecho], reglas=[regla])


def test_caso_7_ejecutar_un_paso_regla_individual():
    """
    Caso 7:
    Evaluar una regla individualmente en simulación paso a paso:
    - Si cumple, se activa, devuelve su conclusión y actualiza la memoria.
    - Si no cumple, queda rechazada.
    """
    id_temp = uuid4()
    id_diag = uuid4()
    mapa = {str(id_temp): "temperatura", str(id_diag): "diagnostico"}

    r_fiebre = Regla(
        id=uuid4(),
        nombre="Regla_Fiebre",
        prioridad=10,
        condiciones=[Condicion(hecho_id=id_temp, operador=OperadorCondicion.MAYOR, valor_esperado="38.0")],
        conclusiones=[Conclusion(hecho_resultante_id=id_diag, valor_resultante="Fiebre Alta")],
    )

    motor = MotorInferencia()

    # 1. Caso no cumple (37.0 < 38.0) -> RECHAZADA
    paso_no_cumple = motor.ejecutar_un_paso_regla(
        memoria_trabajo={"temperatura": 37.0},
        regla=r_fiebre,
        numero_paso=1,
        mapa_ids_a_nombres=mapa,
    )
    assert not paso_no_cumple.finalizado
    assert paso_no_cumple.regla_disparada is None
    assert len(paso_no_cumple.hechos_generados) == 0
    assert any(t.estado == EstadoReglaInferencia.RECHAZADA for t in paso_no_cumple.trazas_paso)

    # 2. Caso cumple (39.0 > 38.0) -> ACTIVADA y EJECUTADA con resultado
    paso_cumple = motor.ejecutar_un_paso_regla(
        memoria_trabajo={"temperatura": 39.0},
        regla=r_fiebre,
        numero_paso=2,
        mapa_ids_a_nombres=mapa,
        es_ultimo_paso=True,
    )
    assert paso_cumple.finalizado
    assert paso_cumple.regla_disparada.id == r_fiebre.id
    assert len(paso_cumple.hechos_generados) == 1
    assert paso_cumple.hechos_generados[0]["nombre"] == "diagnostico"
    assert paso_cumple.hechos_generados[0]["valor"] == "Fiebre Alta"
    assert paso_cumple.memoria_trabajo_post["diagnostico"] == "Fiebre Alta"
    assert any(t.estado == EstadoReglaInferencia.EJECUTADA for t in paso_cumple.trazas_paso)

