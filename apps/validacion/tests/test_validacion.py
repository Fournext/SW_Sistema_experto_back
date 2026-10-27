"""
Pruebas para el módulo de Validación de Bases de Conocimiento (Sprint 2 - HU-18, HU-19).
Verifica detección de inconsistencias estructurales, semánticas, lógicas y reporte de errores.
"""
import pytest
from uuid import uuid4
from django.urls import reverse
from rest_framework import status

from apps.base_conocimiento.entities import BaseConocimiento, Condicion, Conclusion, Hecho, Regla, Variable
from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import (
    AgregarConclusionARegla,
    AgregarCondicionARegla,
    CrearHecho,
    CrearRegla,
    CrearVariable,
)
from apps.sistemas_expertos.services import CrearSistemaExperto
from apps.validacion.engine import MotorValidacion
from apps.validacion.services import (
    ConsultarIncidenciasValidacion,
    ConsultarUltimaValidacion,
    ValidarBaseConocimiento,
)
from compartido.constantes.enums import OperadorCondicion, SeveridadIncidencia, TipoDato


@pytest.mark.parametrize("valor", [None, "", "false", "0"])
def test_hecho_inicial_no_necesita_valor_preasignado_para_ser_alcanzable(valor):
    hecho = Hecho(nombre="Entrada", valor=valor, es_inicial=True)
    salida = Variable(nombre="Resultado")
    regla = Regla(
        nombre="R1",
        condiciones=[Condicion(hecho_id=hecho.id, valor_esperado="true")],
        conclusiones=[Conclusion(variable_resultante_id=salida.id, valor_resultante="Listo")],
    )
    resultado = MotorValidacion.validar(uuid4(), [hecho], [salida], [regla])
    assert not [i for i in resultado.incidencias if i.codigo == "VAL-007"]


@pytest.mark.parametrize("productora_activa", [None, False, True])
def test_hecho_no_inicial_necesita_una_regla_activa_que_lo_produzca(productora_activa):
    entrada = Hecho(nombre="Entrada", es_inicial=True)
    derivado = Hecho(nombre="Derivado", es_inicial=False)
    salida = Variable(nombre="Resultado")
    condicion = Condicion(hecho_id=derivado.id, valor_esperado="true")
    reglas = [Regla(
        nombre="Consumidora", condiciones=[condicion],
        conclusiones=[Conclusion(variable_resultante_id=salida.id, valor_resultante="Listo")],
    )]
    if productora_activa is not None:
        reglas.append(Regla(
            nombre="Productora", activa=productora_activa,
            condiciones=[Condicion(hecho_id=entrada.id, valor_esperado="true")],
            conclusiones=[Conclusion(hecho_resultante_id=derivado.id, valor_resultante="true")],
        ))
    resultado = MotorValidacion.validar(uuid4(), [entrada, derivado], [salida], reglas)
    incidencias = [i for i in resultado.incidencias if i.codigo == "VAL-007"]
    assert len(incidencias) == (0 if productora_activa else 1)
    if incidencias:
        assert incidencias[0].entidad_id == condicion.id

@pytest.fixture
def se_con_base(db):
    se = CrearSistemaExperto().ejecutar(nombre="SE Validacion Test")
    bc = BaseConocimientoModel.objects.get(sistema_experto_id=se.id)
    return se, bc


@pytest.mark.django_db
def test_api_reporte_no_advierte_por_hecho_inicial_sin_valor(api_client, se_con_base):
    _, base = se_con_base
    hecho = CrearHecho().ejecutar(
        base_conocimiento_id=base.id, nombre="Wifi Activo", tipo_dato="BOOLEANO", es_inicial=True,
    )
    variable = CrearVariable().ejecutar(base_conocimiento_id=base.id, nombre="Diagnóstico")
    regla = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="R01")
    AgregarCondicionARegla().ejecutar(regla_id=regla.id, hecho_id=hecho.id, operador="=", valor_esperado="false")
    AgregarConclusionARegla().ejecutar(regla_id=regla.id, variable_resultante_id=variable.id, valor_resultante="WiFi desactivado")
    respuesta = api_client.post(reverse("validacion:base_conocimiento_validar", kwargs={"id": base.id}))
    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["data"]["total_advertencias"] == 0
    reporte = api_client.get(reverse("validacion:validacion_incidencias_list", kwargs={"id": respuesta.data["data"]["id"]}))
    assert reporte.status_code == status.HTTP_200_OK
    assert not [i for i in reporte.data["data"] if i["codigo"] == "VAL-007"]


@pytest.mark.django_db
def test_validacion_base_valida_sin_errores(se_con_base):
    """HU-18: Una base de conocimiento bien formada arroja es_valida = True y 0 errores."""
    se, bc = se_con_base

    h_luz = CrearHecho().ejecutar(
        base_conocimiento_id=bc.id, nombre="hay_luz", valor="true", tipo_dato="BOOLEANO"
    )
    v_estado = CrearVariable().ejecutar(
        base_conocimiento_id=bc.id, nombre="estado_lampara", tipo_dato="TEXTO"
    )
    r1 = CrearRegla().ejecutar(
        base_conocimiento_id=bc.id, nombre="Regla_Encendido", prioridad=10, activa=True
    )
    AgregarCondicionARegla().ejecutar(
        regla_id=r1.id, hecho_id=h_luz.id, operador="=", valor_esperado="true"
    )
    AgregarConclusionARegla().ejecutar(
        regla_id=r1.id, variable_resultante_id=v_estado.id, valor_resultante="Encendida"
    )

    caso_uso = ValidarBaseConocimiento()
    resultado = caso_uso.ejecutar(bc.id)

    assert resultado.es_valida is True
    assert resultado.total_errores == 0


@pytest.mark.django_db
def test_deteccion_reglas_duplicadas_val001(se_con_base):
    """HU-18: Detección de reglas idénticas en condiciones y conclusiones (VAL-001)."""
    se, bc = se_con_base

    h1 = CrearHecho().ejecutar(
        base_conocimiento_id=bc.id, nombre="sensor_activo", valor="true", tipo_dato="BOOLEANO"
    )
    v1 = CrearVariable().ejecutar(
        base_conocimiento_id=bc.id, nombre="alarma", tipo_dato="TEXTO"
    )

    r1 = CrearRegla().ejecutar(
        base_conocimiento_id=bc.id, nombre="Regla_Alarma_1", prioridad=10, activa=True
    )
    AgregarCondicionARegla().ejecutar(regla_id=r1.id, hecho_id=h1.id, operador="=", valor_esperado="true")
    AgregarConclusionARegla().ejecutar(regla_id=r1.id, variable_resultante_id=v1.id, valor_resultante="DISPARADA")

    r2 = CrearRegla().ejecutar(
        base_conocimiento_id=bc.id, nombre="Regla_Alarma_2", prioridad=10, activa=True
    )
    AgregarCondicionARegla().ejecutar(regla_id=r2.id, hecho_id=h1.id, operador="=", valor_esperado="true")
    AgregarConclusionARegla().ejecutar(regla_id=r2.id, variable_resultante_id=v1.id, valor_resultante="DISPARADA")

    caso_uso = ValidarBaseConocimiento()
    resultado = caso_uso.ejecutar(bc.id)

    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-001" in codigos


@pytest.mark.django_db
def test_deteccion_reglas_contradictorias_val002(se_con_base):
    """HU-18: Detección de reglas contradictorias con mismas condiciones y resultados opuestos (VAL-002)."""
    se, bc = se_con_base

    h1 = CrearHecho().ejecutar(
        base_conocimiento_id=bc.id, nombre="lluvia", valor="true", tipo_dato="BOOLEANO"
    )
    v1 = CrearVariable().ejecutar(
        base_conocimiento_id=bc.id, nombre="salir_con_paraguas", tipo_dato="TEXTO"
    )

    r1 = CrearRegla().ejecutar(
        base_conocimiento_id=bc.id, nombre="Regla_Lluvia_SI", prioridad=10, activa=True
    )
    AgregarCondicionARegla().ejecutar(regla_id=r1.id, hecho_id=h1.id, operador="=", valor_esperado="true")
    AgregarConclusionARegla().ejecutar(regla_id=r1.id, variable_resultante_id=v1.id, valor_resultante="SI")

    r2 = CrearRegla().ejecutar(
        base_conocimiento_id=bc.id, nombre="Regla_Lluvia_NO", prioridad=10, activa=True
    )
    AgregarCondicionARegla().ejecutar(regla_id=r2.id, hecho_id=h1.id, operador="=", valor_esperado="true")
    AgregarConclusionARegla().ejecutar(regla_id=r2.id, variable_resultante_id=v1.id, valor_resultante="NO")

    caso_uso = ValidarBaseConocimiento()
    resultado = caso_uso.ejecutar(bc.id)

    assert resultado.es_valida is False
    assert resultado.total_errores >= 1
    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-002" in codigos


@pytest.mark.django_db
def test_deteccion_reglas_incompletas_val004_val005(se_con_base):
    """HU-18: Reglas sin condiciones (VAL-004) y sin conclusiones (VAL-005)."""
    se, bc = se_con_base

    # Regla sin condiciones
    r_vacia = CrearRegla().ejecutar(
        base_conocimiento_id=bc.id, nombre="Regla_Vacia", activa=True
    )

    caso_uso = ValidarBaseConocimiento()
    resultado = caso_uso.ejecutar(bc.id)

    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-004" in codigos
    assert "VAL-005" in codigos


@pytest.mark.django_db
def test_deteccion_variables_huerfanas_val006(se_con_base):
    """HU-18: Detección de variables no utilizadas (VAL-006)."""
    se, bc = se_con_base

    CrearVariable().ejecutar(
        base_conocimiento_id=bc.id, nombre="variable_olvidada", tipo_dato="TEXTO"
    )

    caso_uso = ValidarBaseConocimiento()
    resultado = caso_uso.ejecutar(bc.id)

    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-006" in codigos


@pytest.mark.django_db
def test_api_rest_validacion_y_reporte_incidencias(api_client, se_con_base):
    """HU-18 y HU-19: Ejecución y consulta de validación y reporte de incidencias por API."""
    se, bc = se_con_base

    # Crear una regla sin condiciones ni conclusiones para forzar incidencias
    CrearRegla().ejecutar(base_conocimiento_id=bc.id, nombre="Regla Incompleta", activa=True)

    # 1. Ejecutar validación
    url_val = reverse("validacion:base_conocimiento_validar", kwargs={"id": bc.id})
    resp_val = api_client.post(url_val)
    assert resp_val.status_code == status.HTTP_201_CREATED
    val_id = resp_val.data["data"]["id"]
    assert resp_val.data["data"]["total_errores"] >= 1

    # 2. Consultar última validación
    url_ult = reverse("validacion:base_conocimiento_ultima_validacion", kwargs={"id": bc.id})
    resp_ult = api_client.get(url_ult)
    assert resp_ult.status_code == status.HTTP_200_OK
    assert resp_ult.data["data"]["id"] == val_id

    # 3. Consultar reporte de incidencias con sugerencias (HU-19)
    url_inc = reverse("validacion:validacion_incidencias_list", kwargs={"id": val_id})
    resp_inc = api_client.get(f"{url_inc}?severidad=ERROR")
    assert resp_inc.status_code == status.HTTP_200_OK
    assert len(resp_inc.data["data"]) >= 1
    primera_inc = resp_inc.data["data"][0]
    assert "sugerencia" in primera_inc
    assert "posible_causa" in primera_inc
    assert primera_inc["severidad"] == "ERROR"
