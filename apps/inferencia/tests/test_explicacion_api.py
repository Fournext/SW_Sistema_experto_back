from decimal import Decimal

import pytest

from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import (
    AgregarConclusionARegla, AgregarCondicionARegla, CrearHecho, CrearRegla, CrearVariable,
)
from apps.inferencia.models import ExplicacionConclusionModel
from apps.inferencia.services import AvanzarPasoSimulacion, EjecutarInferencia, IniciarSimulacion
from apps.sistemas_expertos.services import CrearSistemaExperto


@pytest.mark.django_db
@pytest.mark.parametrize("simulacion", [False, True])
def test_api_explicacion_enriquece_corrida_persistida_con_cadena_real_y_nombres(api_client, simulacion):
    sistema = CrearSistemaExperto().ejecutar(nombre="Explicación humana")
    base = BaseConocimientoModel.objects.get(sistema_experto_id=sistema.id)
    inicial = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="Dato inicial", valor="true", tipo_dato="BOOLEANO")
    intermedio = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="Dato derivado", valor="false", tipo_dato="BOOLEANO", es_inicial=False)
    irrelevante = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="Dato ajeno", valor="false", tipo_dato="BOOLEANO")
    salida = CrearVariable().ejecutar(base_conocimiento_id=base.id, nombre="Diagnóstico", tipo_dato="TEXTO")
    primera = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="R1 habilitar", prioridad=10, factor_certeza=Decimal("0.70"))
    segunda = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="R2 concluir", prioridad=5)
    rechazada = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="R3 rechazada", prioridad=1)
    for regla, hecho in [(primera, inicial), (segunda, intermedio), (rechazada, irrelevante)]:
        AgregarCondicionARegla().ejecutar(regla_id=regla.id, hecho_id=hecho.id, operador="=", valor_esperado="true")
    AgregarConclusionARegla().ejecutar(regla_id=primera.id, hecho_resultante_id=intermedio.id, valor_resultante="true")
    AgregarConclusionARegla().ejecutar(regla_id=segunda.id, variable_resultante_id=salida.id, valor_resultante="Aprobado")
    if simulacion:
        sesion = IniciarSimulacion().ejecutar(sistema.id)
        for _ in range(10):
            if AvanzarPasoSimulacion().ejecutar(sesion.id, modo_evaluacion="POR_REGLA")["finalizado"]:
                break
        ejecucion_id = sesion.id
    else:
        ejecucion_id = EjecutarInferencia().ejecutar(sistema.id).ejecucion_id

    # La explicación simple ya persistida no debe bloquear la respuesta enriquecida.
    assert ExplicacionConclusionModel.objects.filter(ejecucion_id=ejecucion_id).exists()
    url = f"/api/v1/inferencias/{ejecucion_id}/explicacion/"
    respuesta = api_client.get(url)
    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["conclusion"] == data["conclusion_valor"] == "Aprobado"
    assert data["conclusion_nombre"] == "Diagnóstico"
    assert data["factor_certeza_final"] is None
    assert data["hechos_iniciales_relevantes"] == [{"nombre": "Dato inicial", "valor": True if simulacion else "true"}]
    assert [h["nombre"] for h in data["hechos_intermedios_derivados"]] == ["Dato derivado"]
    assert [r["id"] for r in data["reglas_disparadas"]] == [str(primera.id), str(segunda.id)]
    assert data["reglas_disparadas"][0] == {
        "id": str(primera.id), "nombre": "R1 habilitar", "prioridad": 10, "factor_certeza": 0.7,
        "condiciones_cumplidas": ["Dato inicial = true"], "consecuencia": "Dato derivado = true",
    }
    assert data["reglas_disparadas"][1]["factor_certeza"] is None
    assert data["reglas_disparadas"][1]["condiciones_cumplidas"] == ["Dato derivado = true"]
    assert data["reglas_disparadas"][1]["consecuencia"] == "Diagnóstico = Aprobado"
    assert len(data["cadena_razonamiento"]) == 2
    assert str(inicial.id) not in " ".join(data["cadena_razonamiento"])
    assert "Diagnóstico = Aprobado" in data["resumen_explicativo"]
    assert data["arbol"]["tipo"] == "CADENA_CAUSAL"
    assert "R1 habilitar" in data["texto"]
    assert data["reglas_involucradas"] == ["R1 habilitar", "R2 concluir"]

    ExplicacionConclusionModel.objects.filter(ejecucion_id=ejecucion_id).delete()
    respuesta = api_client.get(url)
    assert respuesta.status_code == 200
    assert respuesta.json()["data"] == data


@pytest.mark.django_db
def test_api_explicacion_sin_conclusion_no_inventa_certeza_ni_reglas(api_client):
    sistema = CrearSistemaExperto().ejecutar(nombre="Sin deducciones")
    ejecucion_id = EjecutarInferencia().ejecutar(sistema.id).ejecucion_id
    respuesta = api_client.get(f"/api/v1/inferencias/{ejecucion_id}/explicacion/")
    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["conclusion_valor"] is None
    assert data["conclusion_nombre"] is None
    assert data["factor_certeza_final"] is None
    assert data["reglas_disparadas"] == []
    assert data["cadena_razonamiento"] == []
    assert data["hechos_iniciales_relevantes"] == []
    assert "No se alcanzó" in data["resumen_explicativo"]
