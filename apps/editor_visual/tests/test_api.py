"""
Pruebas de endpoints REST para el Editor Visual.
"""
import pytest
from rest_framework import status
from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import CrearHecho
from apps.sistemas_expertos.services import CrearSistemaExperto


@pytest.fixture
def setup_editor_api(db):
    se = CrearSistemaExperto().ejecutar(nombre="SE Editor API")
    bc = BaseConocimientoModel.objects.get(sistema_experto_id=se.id)
    h1 = CrearHecho().ejecutar(base_conocimiento_id=bc.id, nombre="h_api1", valor="true")
    h2 = CrearHecho().ejecutar(base_conocimiento_id=bc.id, nombre="h_api2", valor="false")
    return {"se_id": se.id, "h1_id": h1.id, "h2_id": h2.id}


@pytest.mark.django_db
def test_api_editor_completo(api_client, setup_editor_api):
    se_id = setup_editor_api["se_id"]
    h1_id = setup_editor_api["h1_id"]
    h2_id = setup_editor_api["h2_id"]

    # 1. Crear nodo 1
    res_n1 = api_client.post(
        f"/api/v1/sistemas-expertos/{se_id}/nodos/",
        data={"tipo": "HECHO", "referencia_id": str(h1_id), "posicion_x": 10.0, "posicion_y": 20.0},
        format="json",
    )
    assert res_n1.status_code == status.HTTP_201_CREATED
    nodo1_id = res_n1.json()["data"]["id"]

    # 2. Crear nodo 2
    res_n2 = api_client.post(
        f"/api/v1/sistemas-expertos/{se_id}/nodos/",
        data={"tipo": "HECHO", "referencia_id": str(h2_id), "posicion_x": 100.0, "posicion_y": 200.0},
        format="json",
    )
    assert res_n2.status_code == status.HTTP_201_CREATED
    nodo2_id = res_n2.json()["data"]["id"]

    # 3. Mover nodo 1
    res_mover = api_client.patch(
        f"/api/v1/nodos/{nodo1_id}/",
        data={"posicion_x": 55.0, "posicion_y": 75.0},
        format="json",
    )
    assert res_mover.status_code == status.HTTP_200_OK

    # 4. Crear conexión
    res_con = api_client.post(
        f"/api/v1/sistemas-expertos/{se_id}/conexiones/",
        data={"nodo_origen_id": nodo1_id, "nodo_destino_id": nodo2_id, "etiqueta": "Prueba"},
        format="json",
    )
    assert res_con.status_code == status.HTTP_201_CREATED
    con_id = res_con.json()["data"]["id"]

    # 5. Obtener lienzo
    res_lienzo = api_client.get(f"/api/v1/sistemas-expertos/{se_id}/editor/")
    assert res_lienzo.status_code == status.HTTP_200_OK
    data_lienzo = res_lienzo.json()["data"]
    assert len(data_lienzo["nodos"]) == 2
    assert len(data_lienzo["conexiones"]) == 1

    # 6. Eliminar conexión
    res_del_con = api_client.delete(f"/api/v1/conexiones/{con_id}/")
    assert res_del_con.status_code == status.HTTP_204_NO_CONTENT

    # 7. Eliminar nodo
    res_del_nodo = api_client.delete(f"/api/v1/nodos/{nodo1_id}/")
    assert res_del_nodo.status_code == status.HTTP_204_NO_CONTENT
