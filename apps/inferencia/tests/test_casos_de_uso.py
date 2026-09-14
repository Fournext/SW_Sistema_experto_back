"""
Pruebas de casos de uso para el módulo de Inferencia con persistencia.
"""
import pytest
from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import (
    AgregarConclusionARegla,
    AgregarCondicionARegla,
    CrearHecho,
    CrearRegla,
)
from apps.inferencia.services import (
    ConsultarEjecucion,
    ConsultarTrazaInferencia,
    EjecutarInferencia,
)
from apps.sistemas_expertos.services import CrearSistemaExperto
from compartido.constantes.enums import EstadoEjecucion


@pytest.fixture
def se_con_reglas(db):
    se = CrearSistemaExperto().ejecutar(nombre="SE Inferencia Casos")
    bc = BaseConocimientoModel.objects.get(sistema_experto_id=se.id)

    h_luz = CrearHecho().ejecutar(
        base_conocimiento_id=bc.id, nombre="hay_luz", valor="true", tipo_dato="BOOLEANO"
    )
    h_foco = CrearHecho().ejecutar(
        base_conocimiento_id=bc.id,
        nombre="foco_encendido",
        valor=None,
        tipo_dato="BOOLEANO",
        es_inicial=False,
    )

    regla = CrearRegla().ejecutar(
        base_conocimiento_id=bc.id, nombre="Regla_Luz", prioridad=5, activa=True
    )
    AgregarCondicionARegla().ejecutar(
        regla_id=regla.id, hecho_id=h_luz.id, operador="=", valor_esperado="true"
    )
    AgregarConclusionARegla().ejecutar(
        regla_id=regla.id, hecho_resultante_id=h_foco.id, valor_resultante="true"
    )

    return se


@pytest.mark.django_db
def test_ejecutar_inferencia_y_consultar_traza(se_con_reglas):
    se = se_con_reglas
    caso_inferencia = EjecutarInferencia()
    resultado = caso_inferencia.ejecutar(sistema_experto_id=se.id)

    assert resultado.ejecucion_id is not None
    assert resultado.estado == EstadoEjecucion.FINALIZADA
    assert resultado.conclusion_final == "true"
    assert len(resultado.hechos_generados) >= 1

    # Consultar ejecución
    consultar = ConsultarEjecucion()
    ejecucion = consultar.ejecutar(id_ejecucion=resultado.ejecucion_id)
    assert ejecucion.id == resultado.ejecucion_id
    assert ejecucion.conclusion_final == "true"

    # Consultar traza
    traza = ConsultarTrazaInferencia()
    detalles = traza.ejecutar(id_ejecucion=resultado.ejecucion_id)
    assert len(detalles) > 0
    estados = [d.estado_regla.value for d in detalles]
    assert "EJECUTADA" in estados
