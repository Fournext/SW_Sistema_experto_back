import pytest

from apps.base_conocimiento.models import BaseConocimientoModel, HechoModel
from apps.base_conocimiento.services import (
    AgregarConclusionARegla, AgregarCondicionARegla, CrearHecho, CrearRegla, CrearVariable,
)
from apps.sistemas_expertos.services import CrearSistemaExperto


@pytest.mark.django_db
def test_api_directa_respeta_ids_y_tipos_al_sobrescribir_datos_iniciales(api_client):
    sistema = CrearSistemaExperto().ejecutar(nombre="Directo con respuestas")
    base = BaseConocimientoModel.objects.get(sistema_experto_id=sistema.id)
    entrada = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="entrada", valor="false", tipo_dato="BOOLEANO")
    respaldo = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="respaldo", valor="true", tipo_dato="BOOLEANO")
    salida = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="salida", valor=None,
                                 tipo_dato="TEXTO", es_inicial=False)
    nivel = CrearVariable().ejecutar(base_conocimiento_id=base.id, nombre="nivel", tipo_dato="ENTERO")
    regla = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="R1", prioridad=1, activa=True)
    for hecho in [entrada, respaldo]:
        AgregarCondicionARegla().ejecutar(regla_id=regla.id, hecho_id=hecho.id, operador="=", valor_esperado="true")
    AgregarCondicionARegla().ejecutar(regla_id=regla.id, variable_id=nivel.id, operador=">", valor_esperado="3")
    AgregarConclusionARegla().ejecutar(regla_id=regla.id, hecho_resultante_id=salida.id, valor_resultante="Aprobado")

    response = api_client.post(f"/api/v1/sistemas-expertos/{sistema.id}/inferencias/", {
        "hechos_iniciales": [{"nombre": " ENTRADA ", "valor": "true"}, {"nombre": " Nivel ", "valor": "5"}],
    }, format="json")
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["conclusion_final"] == "Aprobado"
    assert [(t["regla_id"], t["estado"]) for t in data["reglas_evaluadas"]] == [
        (str(regla.id), "EVALUADA"), (str(regla.id), "ACTIVADA"), (str(regla.id), "EJECUTADA"),
    ]
    assert data["hechos_generados"] == [{"nombre": "salida", "valor": "Aprobado"}]
    memoria = {h["nombre"]: h["valor"] for h in data["hechos_iniciales"]}
    assert memoria["entrada"] is True
    assert memoria["respaldo"] is True
    assert memoria["nivel"] == 5
    assert HechoModel.objects.get(pk=entrada.id).valor == "false"
    assert HechoModel.objects.get(pk=salida.id).valor is None
    assert HechoModel.objects.filter(base_conocimiento_id=base.id).count() == 3
