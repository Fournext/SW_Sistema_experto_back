"""
Pruebas de endpoints REST para Sistemas Expertos.
"""
import pytest
from uuid import uuid4
from rest_framework import status


@pytest.mark.django_db
def test_api_crear_sistema_experto_201(api_client):
    payload = {
        "nombre": "Experto en Redes",
        "descripcion": "Diagnóstico de conectividad",
        "estado": "ACTIVO",
    }
    response = api_client.post("/api/v1/sistemas-expertos/", data=payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert data["data"]["nombre"] == "Experto en Redes"
    assert "id" in data["data"]


@pytest.mark.django_db
def test_api_crear_sistema_experto_400_nombre_vacio(api_client):
    payload = {"nombre": ""}
    response = api_client.post("/api/v1/sistemas-expertos/", data=payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["success"] is False


@pytest.mark.django_db
def test_api_listar_sistemas_expertos_200(api_client):
    api_client.post("/api/v1/sistemas-expertos/", data={"nombre": "SE 1"}, format="json")
    api_client.post("/api/v1/sistemas-expertos/", data={"nombre": "SE 2"}, format="json")

    response = api_client.get("/api/v1/sistemas-expertos/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 2


@pytest.mark.django_db
def test_api_obtener_sistema_experto_404(api_client):
    id_falso = uuid4()
    response = api_client.get(f"/api/v1/sistemas-expertos/{id_falso}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["success"] is False


@pytest.mark.django_db
def test_api_actualizar_y_eliminar_sistema_experto(api_client):
    crear_res = api_client.post("/api/v1/sistemas-expertos/", data={"nombre": "Inicial"}, format="json")
    se_id = crear_res.json()["data"]["id"]

    # PUT
    put_res = api_client.put(
        f"/api/v1/sistemas-expertos/{se_id}/",
        data={"nombre": "Actualizado Total", "descripcion": "Desc", "estado": "ARCHIVADO"},
        format="json",
    )
    assert put_res.status_code == status.HTTP_200_OK
    assert put_res.json()["data"]["nombre"] == "Actualizado Total"

    # PATCH
    patch_res = api_client.patch(
        f"/api/v1/sistemas-expertos/{se_id}/",
        data={"nombre": "Actualizado Parcial"},
        format="json",
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["data"]["nombre"] == "Actualizado Parcial"

    # DELETE
    del_res = api_client.delete(f"/api/v1/sistemas-expertos/{se_id}/")
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # Verificar 404 tras borrar
    get_res = api_client.get(f"/api/v1/sistemas-expertos/{se_id}/")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND
