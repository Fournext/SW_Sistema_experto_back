"""
Pruebas de endpoints REST para Base de Conocimiento (Hechos, Variables, Reglas, Condiciones, Conclusiones).
"""
import pytest
from rest_framework import status
from apps.base_conocimiento.models import BaseConocimientoModel
from apps.sistemas_expertos.services import CrearSistemaExperto


@pytest.fixture
def setup_bc(db):
    se = CrearSistemaExperto().ejecutar(nombre="SE API BC")
    bc = BaseConocimientoModel.objects.get(sistema_experto_id=se.id)
    return {"se_id": se.id, "bc_id": bc.id}


@pytest.mark.django_db
def test_api_hechos_crud(api_client, setup_bc):
    bc_id = setup_bc["bc_id"]

    # POST Hecho
    payload = {"nombre": "humedad_alta", "valor": "true", "tipo_dato": "BOOLEANO", "es_inicial": True}
    res_post = api_client.post(f"/api/v1/bases-conocimiento/{bc_id}/hechos/", data=payload, format="json")
    assert res_post.status_code == status.HTTP_201_CREATED
    hecho_id = res_post.json()["data"]["id"]

    # GET Hecho
    res_get = api_client.get(f"/api/v1/hechos/{hecho_id}/")
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.json()["data"]["nombre"] == "humedad_alta"

    # PUT Hecho
    res_put = api_client.put(
        f"/api/v1/hechos/{hecho_id}/",
        data={"nombre": "humedad_media", "valor": "false", "tipo_dato": "BOOLEANO", "es_inicial": False},
        format="json",
    )
    assert res_put.status_code == status.HTTP_200_OK
    assert res_put.json()["data"]["nombre"] == "humedad_media"

    # DELETE Hecho
    res_del = api_client.delete(f"/api/v1/hechos/{hecho_id}/")
    assert res_del.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_api_reglas_con_condiciones_y_conclusiones(api_client, setup_bc):
    bc_id = setup_bc["bc_id"]

    # 1. Crear hecho premisa
    res_h = api_client.post(
        f"/api/v1/bases-conocimiento/{bc_id}/hechos/",
        data={"nombre": "h_test", "valor": "1"},
        format="json",
    )
    hecho_id = res_h.json()["data"]["id"]

    # 2. Crear regla
    payload_regla = {
        "nombre": "Regla Demo",
        "descripcion": "Demo API",
        "prioridad": 8,
        "factor_certeza": 0.85,
        "activa": True,
    }
    res_r = api_client.post(f"/api/v1/bases-conocimiento/{bc_id}/reglas/", data=payload_regla, format="json")
    assert res_r.status_code == status.HTTP_201_CREATED
    regla_id = res_r.json()["data"]["id"]

    # 3. Agregar condición a la regla
    payload_cond = {
        "hecho_id": hecho_id,
        "operador": "=",
        "valor_esperado": "1",
        "orden": 1,
    }
    res_c = api_client.post(f"/api/v1/reglas/{regla_id}/condiciones/", data=payload_cond, format="json")
    assert res_c.status_code == status.HTTP_201_CREATED

    # 4. Agregar conclusión a la regla
    payload_conc = {
        "hecho_resultante_id": hecho_id,
        "valor_resultante": "2",
    }
    res_conc = api_client.post(f"/api/v1/reglas/{regla_id}/conclusiones/", data=payload_conc, format="json")
    assert res_conc.status_code == status.HTTP_201_CREATED

    res_regla_det = api_client.get(f"/api/v1/reglas/{regla_id}/")
    assert res_regla_det.status_code == status.HTTP_200_OK
    data = res_regla_det.json()["data"]
    assert len(data["condiciones"]) == 1
    assert len(data["conclusiones"]) == 1


@pytest.mark.django_db
def test_api_variables_es_inicial_y_pregunta(api_client, setup_bc):
    bc_id = setup_bc["bc_id"]

    # 1. Crear variable inicial con pregunta
    payload_var = {
        "nombre": "temperatura_paciente",
        "tipo_dato": "DECIMAL",
        "es_inicial": True,
        "pregunta": "¿Cuál es la temperatura actual?",
        "valor_defecto": "36.5",
    }
    res_post = api_client.post(f"/api/v1/bases-conocimiento/{bc_id}/variables/", data=payload_var, format="json")
    assert res_post.status_code == status.HTTP_201_CREATED
    data_post = res_post.json()["data"]
    assert data_post["es_inicial"] is True
    assert data_post["pregunta"] == "¿Cuál es la temperatura actual?"
    var_id = data_post["id"]

    # 2. Consultar por ID
    res_get = api_client.get(f"/api/v1/variables/{var_id}/")
    assert res_get.status_code == status.HTTP_200_OK
    data_get = res_get.json()["data"]
    assert data_get["es_inicial"] is True
    assert data_get["pregunta"] == "¿Cuál es la temperatura actual?"

    # 3. Modificar a no inicial
    res_patch = api_client.patch(
        f"/api/v1/variables/{var_id}/",
        data={"es_inicial": False, "pregunta": None},
        format="json",
    )
    assert res_patch.status_code == status.HTTP_200_OK
    data_patch = res_patch.json()["data"]
    assert data_patch["es_inicial"] is False
    assert data_patch["pregunta"] is None
