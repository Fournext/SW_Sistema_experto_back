import pytest

from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import CrearRegla
from apps.inferencia.models import DetalleInferenciaModel, EjecucionInferenciaModel, PasoInferenciaModel
from apps.inferencia.serializers import HistorialInferenciaSalidaSerializer
from apps.inferencia.services import ConsultarHistorialInferencia, EjecutarInferencia
from apps.sistemas_expertos.services import CrearSistemaExperto


def crear_historial(sistema, visual=True, metadatos=True):
    base = BaseConocimientoModel.objects.get(sistema_experto_id=sistema.id)
    regla = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="Regla historial", prioridad=1)
    ejecucion = EjecucionInferenciaModel.objects.create(sistema_experto_id=sistema.id,
                                                      es_simulacion=True, modo="SIMULACION", paso_actual=3)
    orden = 0
    for numero, estados in [(1, ["EVALUADA", "RECHAZADA"]), (2, ["EVALUADA", "ACTIVADA", "EJECUTADA"]),
                            (3, ["EVALUADA", "RECHAZADA"])]:
        PasoInferenciaModel.objects.create(ejecucion=ejecucion, numero_paso=numero,
                                          regla_disparada_id=regla.id if numero == 2 else None)
        for estado in estados:
            orden += 1
            DetalleInferenciaModel.objects.create(ejecucion=ejecucion, regla_id=regla.id, orden=orden,
                estado_regla=estado, paso_numero=numero if metadatos else None,
                paso_visual=(1 if numero < 3 else 2) if visual else None)
    return ejecucion


@pytest.mark.django_db
@pytest.mark.parametrize("visual,metadatos,esperado", [(True, True, 2), (False, True, 3), (False, False, 3)])
def test_historial_cuenta_pasos_logicos_y_evaluaciones_sin_duplicar_estados(api_client, visual, metadatos, esperado):
    sistema = CrearSistemaExperto().ejecutar(nombre="Contadores historial")
    ejecucion = crear_historial(sistema, visual, metadatos)
    respuesta = api_client.get("/api/v1/inferencias/", {"sistema_id": str(sistema.id)})
    assert respuesta.status_code == 200
    registros = respuesta.json()["data"]
    assert len(registros) == 1
    fila = registros[0]
    assert fila["id"] == str(ejecucion.id)
    assert fila["fecha_inicio"]
    assert fila["es_simulacion"] is True
    assert fila["total_pasos"] == esperado
    assert fila["total_reglas_evaluadas"] == 3
    assert fila["total_reglas_disparadas"] == 1


@pytest.mark.django_db
def test_historial_filtra_sistema_estado_aliases_y_modos_legacy(api_client):
    sistema = CrearSistemaExperto().ejecutar(nombre="Sistema propio")
    ajeno = CrearSistemaExperto().ejecutar(nombre="Sistema ajeno")
    directo = EjecucionInferenciaModel.objects.create(sistema_experto_id=sistema.id, es_simulacion=False,
                                                     modo="AUTOMATICA", estado="FINALIZADA")
    simulacion = EjecucionInferenciaModel.objects.create(sistema_experto_id=sistema.id, es_simulacion=True,
                                                        modo="SIMULACION", estado="PAUSADA")
    legacy = EjecucionInferenciaModel.objects.create(sistema_experto_id=sistema.id, es_simulacion=True,
                                                    modo="PASO_A_PASO", estado="FINALIZADA")
    EjecucionInferenciaModel.objects.create(sistema_experto_id=ajeno.id, es_simulacion=True,
                                           modo="SIMULACION", estado="FINALIZADA")
    casos = [
        ({}, {directo.id, simulacion.id, legacy.id}),
        ({"modo": "DIRECTO"}, {directo.id}),
        ({"modo": "SIMULACION_PASO_A_PASO"}, {simulacion.id, legacy.id}),
        ({"modo": "AUTOMATICA"}, {directo.id}),
        ({"modo": "SIMULACION"}, {simulacion.id}),
        ({"modo": "PASO_A_PASO"}, {legacy.id}),
        ({"modo": "SIMULACION_PASO_A_PASO", "estado": "FINALIZADA"}, {legacy.id}),
        ({"estado": "PAUSADA"}, {simulacion.id}),
    ]
    for filtros, esperados in casos:
        respuesta = api_client.get("/api/v1/inferencias/", {"sistema_id": str(sistema.id), **filtros})
        assert respuesta.status_code == 200
        assert {fila["id"] for fila in respuesta.json()["data"]} == {str(id) for id in esperados}


@pytest.mark.django_db
def test_respuestas_custom_en_directo_se_registran_como_directo_en_historial(api_client):
    sistema = CrearSistemaExperto().ejecutar(nombre="Directo con respuestas en historial")
    resultado = EjecutarInferencia().ejecutar(sistema.id, hechos_personalizados=[{"nombre": "entrada", "valor": "sí"}])
    fila = EjecucionInferenciaModel.objects.get(id=resultado.ejecucion_id)
    assert fila.es_simulacion is False
    assert fila.modo == "AUTOMATICA"
    respuesta = api_client.get("/api/v1/inferencias/", {"sistema_id": str(sistema.id), "modo": "DIRECTO"})
    assert [fila["id"] for fila in respuesta.json()["data"]] == [str(resultado.ejecucion_id)]


@pytest.mark.django_db
def test_historial_agrega_toda_la_lista_en_dos_consultas_sin_n_mas_uno(django_assert_num_queries):
    sistema = CrearSistemaExperto().ejecutar(nombre="Historial por lote")
    crear_historial(sistema)
    for _ in range(5):
        EjecucionInferenciaModel.objects.create(sistema_experto_id=sistema.id, es_simulacion=True, modo="SIMULACION")
    with django_assert_num_queries(2):
        historial = ConsultarHistorialInferencia().ejecutar(sistema_experto_id=sistema.id)
        data = HistorialInferenciaSalidaSerializer(historial, many=True, context={"es_historial": True}).data
    assert len(data) == 6
    assert sum(fila["total_reglas_evaluadas"] for fila in data) == 3
