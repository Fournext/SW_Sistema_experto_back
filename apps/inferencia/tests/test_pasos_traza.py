import pytest

from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import (
    AgregarConclusionARegla, AgregarCondicionARegla, CrearHecho, CrearRegla,
)
from apps.inferencia.repositories import DjangoDetalleInferenciaRepositorio
from apps.inferencia.serializers import ReglaEvaluadaTrazaSerializer
from apps.inferencia.services import AvanzarPasoSimulacion, EjecutarInferencia, IniciarSimulacion
from apps.sistemas_expertos.services import CrearSistemaExperto


@pytest.mark.django_db
@pytest.mark.parametrize("simulacion", [False, True])
def test_regla_rechazada_y_activada_conserva_cada_paso_en_api_y_bd(api_client, simulacion):
    sistema = CrearSistemaExperto().ejecutar(nombre="Reglas por paso")
    base = BaseConocimientoModel.objects.get(sistema_experto_id=sistema.id)
    inicio = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="inicio", valor="true", tipo_dato="BOOLEANO")
    habilitado = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="habilitado", valor="false", tipo_dato="BOOLEANO")
    resultado = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="resultado", valor=None,
                                     tipo_dato="BOOLEANO", es_inicial=False)
    productora = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="R1", prioridad=10, activa=True)
    dependiente = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="R2", prioridad=1, activa=True)
    for regla, entrada, salida in [(productora, inicio, habilitado), (dependiente, habilitado, resultado)]:
        AgregarCondicionARegla().ejecutar(regla_id=regla.id, hecho_id=entrada.id, operador="=", valor_esperado="true")
        AgregarConclusionARegla().ejecutar(regla_id=regla.id, hecho_resultante_id=salida.id, valor_resultante="true")

    if simulacion:
        ejecucion = IniciarSimulacion().ejecutar(sistema_experto_id=sistema.id)
        AvanzarPasoSimulacion().ejecutar(ejecucion.id)
        AvanzarPasoSimulacion().ejecutar(ejecucion.id)
        ejecucion_id = ejecucion.id
    else:
        inferencia = EjecutarInferencia().ejecutar(sistema_experto_id=sistema.id)
        ejecucion_id = inferencia.ejecucion_id
        trazas = ReglaEvaluadaTrazaSerializer(inferencia.reglas_evaluadas, many=True).data
        assert {t["paso_numero"] for t in trazas if t["regla_id"] == str(dependiente.id)} == {1, 2}

    repo = DjangoDetalleInferenciaRepositorio()
    detalles = [d for d in repo.listar_por_ejecucion(ejecucion_id) if d.regla_id == dependiente.id]
    assert [(d.paso_numero, d.estado_regla.value) for d in detalles] == [
        (1, "EVALUADA"), (1, "RECHAZADA"),
        (2, "EVALUADA"), (2, "ACTIVADA"), (2, "EJECUTADA"),
    ]
    assert repo.guardar(detalles[-1]).paso_numero == 2

    response = api_client.get(f"/api/v1/inferencias/{ejecucion_id}/detalles/")
    assert response.status_code == 200
    registros = [d for d in response.json()["data"] if d["regla_id"] == str(dependiente.id)]
    assert [(d["paso_numero"], d["estado"]) for d in registros] == [
        (d.paso_numero, d.estado_regla.value) for d in detalles
    ]

    # Un registro antiguo sin número se conserva desconocido, sin inventar un paso.
    detalles[0].paso_numero = None
    assert repo.guardar(detalles[0]).paso_numero is None
    response = api_client.get(f"/api/v1/inferencias/{ejecucion_id}/detalles/")
    registro_antiguo = next(d for d in response.json()["data"] if d["id"] == str(detalles[0].id))
    assert registro_antiguo["paso_numero"] is None
