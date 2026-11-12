"""
Pruebas de inferencia hacia adelante (FWC) con reglas de premisas complejas (OR, AND, paréntesis).
"""
import pytest
from uuid import uuid4
from apps.base_conocimiento.entities import Hecho, Regla, Conclusion
from apps.inferencia.engine import MotorInferencia
from compartido.constantes.enums import EstadoEjecucion, TipoDato


def test_fwc_regla_con_or_y_and():
    """
    R1: IF (A=b AND B=0) OR P>10 THEN resultado='APROBADO'
    Hechos: A='otro', B=99, P=15 (se cumple por la rama derecha P>10)
    """
    h_a = Hecho(id=uuid4(), nombre="A", valor="otro", tipo_dato=TipoDato.TEXTO)
    h_b = Hecho(id=uuid4(), nombre="B", valor="99", tipo_dato=TipoDato.ENTERO)
    h_p = Hecho(id=uuid4(), nombre="P", valor="15", tipo_dato=TipoDato.ENTERO)

    c_resultado = Conclusion(
        id=uuid4(),
        valor_resultante="APROBADO",
    )

    r1 = Regla(
        id=uuid4(),
        nombre="R1_compleja",
        prioridad=10,
        activa=True,
        expresion_logica="(A=b AND B=0) OR P>10",
        conclusiones=[c_resultado],
    )

    motor = MotorInferencia()
    res = motor.ejecutar(
        hechos_iniciales=[h_a, h_b, h_p],
        reglas=[r1],
    )

    assert res.estado == EstadoEjecucion.FINALIZADA
    assert res.conclusion_final == "APROBADO"
    assert len(res.hechos_generados) == 1
    assert res.hechos_generados[0]["valor"] == "APROBADO"


def test_fwc_regla_con_doble_and_or_anidado():
    """
    R1: IF (A=b AND B=0) OR (P>10 AND P<100) THEN calificacion='VALIDO'
    Caso 1: P=50 -> dispara por rama derecha
    """
    h_a = Hecho(id=uuid4(), nombre="A", valor="c", tipo_dato=TipoDato.TEXTO)
    h_b = Hecho(id=uuid4(), nombre="B", valor="5", tipo_dato=TipoDato.ENTERO)
    h_p = Hecho(id=uuid4(), nombre="P", valor="50", tipo_dato=TipoDato.ENTERO)

    c1 = Conclusion(id=uuid4(), valor_resultante="VALIDO")
    r1 = Regla(
        id=uuid4(),
        nombre="R1_anidada",
        prioridad=10,
        activa=True,
        expresion_logica="(A=b AND B=0) OR (P>10 AND P<100)",
        conclusiones=[c1],
    )

    motor = MotorInferencia()
    res = motor.ejecutar(
        hechos_iniciales=[h_a, h_b, h_p],
        reglas=[r1],
    )

    assert res.conclusion_final == "VALIDO"


def test_fwc_premisas_complejas_con_metas_early_stopping():
    """
    R1: IF (A=b AND B=0) OR P>10 THEN Meta1='LISTO'
    R2: IF Meta1='LISTO' THEN Meta2='FINAL'
    R3: IF Meta2='FINAL' THEN OtraCosa='EXTRA'
    Metas solicitadas: ['Meta1', 'Meta2'].
    R1 y R2 deben disparar y detenerse con motivo METAS_ALCANZADAS.
    """
    from apps.base_conocimiento.entities import Variable

    v_m1 = Variable(id=uuid4(), nombre="Meta1", tipo_dato=TipoDato.TEXTO)
    v_m2 = Variable(id=uuid4(), nombre="Meta2", tipo_dato=TipoDato.TEXTO)
    v_oc = Variable(id=uuid4(), nombre="OtraCosa", tipo_dato=TipoDato.TEXTO)

    h_p = Hecho(id=uuid4(), nombre="P", valor="20", tipo_dato=TipoDato.ENTERO)

    r1 = Regla(
        id=uuid4(),
        nombre="R1",
        prioridad=30,
        activa=True,
        expresion_logica="(A=b AND B=0) OR P>10",
        conclusiones=[Conclusion(id=uuid4(), variable_resultante_id=v_m1.id, valor_resultante="LISTO")],
    )
    r2 = Regla(
        id=uuid4(),
        nombre="R2",
        prioridad=20,
        activa=True,
        expresion_logica="Meta1 = 'LISTO'",
        conclusiones=[Conclusion(id=uuid4(), variable_resultante_id=v_m2.id, valor_resultante="FINAL")],
    )
    r3 = Regla(
        id=uuid4(),
        nombre="R3",
        prioridad=10,
        activa=True,
        expresion_logica="Meta2 = 'FINAL'",
        conclusiones=[Conclusion(id=uuid4(), variable_resultante_id=v_oc.id, valor_resultante="EXTRA")],
    )

    motor = MotorInferencia()
    res = motor.ejecutar(
        hechos_iniciales=[h_p],
        reglas=[r1, r2, r3],
        variables=[v_m1, v_m2, v_oc],
        metas=["Meta1", "Meta2"],
    )

    assert res.motivo_parada == "METAS_ALCANZADAS"
    assert "Meta1" in res.metas_unificadas
    assert "Meta2" in res.metas_unificadas
    assert len(res.metas_pendientes) == 0
    # R3 no debió ejecutarse
    nombres_disparados = [p.regla_disparada.nombre for p in res.pasos if p.regla_disparada]
    assert "R3" not in nombres_disparados
    assert "R1" in nombres_disparados
    assert "R2" in nombres_disparados

