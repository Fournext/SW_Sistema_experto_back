import pytest

from apps.base_conocimiento.models import BaseConocimientoModel, HechoModel, VariableModel
from apps.sistemas_expertos.services import CrearSistemaExperto


@pytest.mark.django_db
@pytest.mark.parametrize("recurso,campo,modelo", [("hechos", "valor", HechoModel), ("variables", "valor_defecto", VariableModel)])
@pytest.mark.parametrize("tipo,valor,esperado", [
    ("TEXTO", "texto", "texto"), ("ENTERO", 0, "0"), ("DECIMAL", 0.0, "0.0"),
    ("BOOLEANO", False, "false"), ("OPCION", "A", "A"),
])
def test_valor_inicial_opcional_se_puede_omitir_y_borrar_sin_perder_cero_o_false(api_client, recurso, campo, modelo, tipo, valor, esperado):
    sistema = CrearSistemaExperto().ejecutar(nombre="Datos opcionales")
    base = BaseConocimientoModel.objects.get(sistema_experto_id=sistema.id)
    lista_url = f"/api/v1/bases-conocimiento/{base.id}/{recurso}/"
    for indice, datos_valor in enumerate([{}, {campo: None}, {campo: ""}]):
        nombre = f"dato_{indice}"
        respuesta = api_client.post(lista_url, {"nombre": nombre, "tipo_dato": tipo, **datos_valor}, format="json")
        assert respuesta.status_code == 201
        assert respuesta.json()["data"][campo] is None

    id_dato = respuesta.json()["data"]["id"]
    detalle_url = f"/api/v1/{recurso}/{id_dato}/"
    respuesta = api_client.patch(detalle_url, {campo: valor}, format="json")
    assert respuesta.status_code == 200
    assert respuesta.json()["data"][campo] == esperado
    # Omitir el campo conserva el valor, tanto en PATCH como en PUT.
    for metodo in [api_client.patch, api_client.put]:
        respuesta = metodo(detalle_url, {"nombre": nombre, "tipo_dato": tipo}, format="json")
        assert respuesta.status_code == 200
        assert respuesta.json()["data"][campo] == esperado

    for metodo, vacio in [(api_client.patch, None), (api_client.put, ""), (api_client.patch, "  ")]:
        api_client.patch(detalle_url, {campo: valor}, format="json")
        respuesta = metodo(detalle_url, {"nombre": nombre, "tipo_dato": tipo, campo: vacio}, format="json")
        assert respuesta.status_code == 200
        assert respuesta.json()["data"][campo] is None
        assert getattr(modelo.objects.get(pk=id_dato), campo) is None
