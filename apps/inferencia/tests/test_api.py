"""
Pruebas de endpoints REST para el módulo de Inferencia.
"""
from django.core.management import call_command
import pytest
from rest_framework import status
from apps.sistemas_expertos.models import SistemaExpertoModel


@pytest.fixture
def se_sembrado(db):
    call_command("seed_sprint1")
    return SistemaExpertoModel.objects.get(
        nombre="Recomendador de metodología de desarrollo"
    )


@pytest.mark.django_db
def test_api_ejecutar_inferencia_retorna_traza_correcta(api_client, se_sembrado):
    se_id = se_sembrado.id
    response = api_client.post(f"/api/v1/sistemas-expertos/{se_id}/inferencias/")

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True

    cuerpo = data["data"]
    assert cuerpo["estado"] == "FINALIZADA"
    assert cuerpo["conclusion_final"] == "Scrum"
    assert len(cuerpo["hechos_iniciales"]) == 3
    assert len(cuerpo["reglas_evaluadas"]) > 0

    # Validar estructura de regla evaluada
    r_eval = [r for r in cuerpo["reglas_evaluadas"] if r["estado"] == "EJECUTADA"][0]
    assert r_eval["regla"] == "R1 - Recomendar Scrum"
    assert r_eval["condiciones_cumplidas"] is True

    ejecucion_id = cuerpo["ejecucion_id"]

    # Consultar ejecución
    res_ejec = api_client.get(f"/api/v1/inferencias/{ejecucion_id}/")
    assert res_ejec.status_code == status.HTTP_200_OK
    assert res_ejec.json()["data"]["conclusion_final"] == "Scrum"

    # Consultar detalles/traza
    res_det = api_client.get(f"/api/v1/inferencias/{ejecucion_id}/detalles/")
    assert res_det.status_code == status.HTTP_200_OK
    assert len(res_det.json()["data"]) > 0
