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


# =========================================================================
# PRUEBAS PARA LOS NUEVOS ANÁLISIS SEMÁNTICO-LÓGICOS (VAL-011 a VAL-017)
# =========================================================================

def test_deteccion_hechos_iniciales_contradictorios_val011():
    """VAL-011: Dos hechos iniciales con el mismo nombre y valores incompatibles generan ERROR."""
    h1 = Hecho(nombre="router_encendido", valor="true", tipo_dato=TipoDato.BOOLEANO, es_inicial=True)
    h2 = Hecho(nombre="router_encendido", valor="false", tipo_dato=TipoDato.BOOLEANO, es_inicial=True)
    v_out = Variable(nombre="salida")
    r1 = Regla(
        nombre="R1",
        condiciones=[Condicion(hecho_id=h1.id, valor_esperado="true")],
        conclusiones=[Conclusion(variable_resultante_id=v_out.id, valor_resultante="ok")],
    )

    resultado = MotorValidacion.validar(uuid4(), [h1, h2], [v_out], [r1])
    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-011" in codigos
    inc = next(i for i in resultado.incidencias if i.codigo == "VAL-011")
    assert inc.severidad == SeveridadIncidencia.ERROR.value
    assert inc.tipo == "LOGICO"


def test_no_contradiccion_hechos_iniciales_con_mismo_valor():
    """Dos hechos iniciales con el mismo valor no generan VAL-011."""
    h1 = Hecho(nombre="router_encendido", valor="true", tipo_dato=TipoDato.BOOLEANO, es_inicial=True)
    h2 = Hecho(nombre="router_encendido", valor="true", tipo_dato=TipoDato.BOOLEANO, es_inicial=True)
    v_out = Variable(nombre="salida")
    r1 = Regla(
        nombre="R1",
        condiciones=[Condicion(hecho_id=h1.id, valor_esperado="true")],
        conclusiones=[Conclusion(variable_resultante_id=v_out.id, valor_resultante="ok")],
    )

    resultado = MotorValidacion.validar(uuid4(), [h1, h2], [v_out], [r1])
    assert not [i for i in resultado.incidencias if i.codigo == "VAL-011"]


def test_deteccion_contradiccion_directa_satisfacibilidad_val012():
    """
    VAL-012: R1 (temp > 38 -> estado=enfermo) y R2 (temp > 40 -> estado=sano).
    Condiciones superpuestas para temp > 40, conclusiones opuestas -> ERROR VAL-012.
    """
    v_temp = Variable(nombre="temperatura", tipo_dato=TipoDato.DECIMAL)
    v_estado = Variable(nombre="estado", tipo_dato=TipoDato.TEXTO)

    r1 = Regla(
        nombre="R01",
        condiciones=[Condicion(variable_id=v_temp.id, operador=OperadorCondicion.MAYOR, valor_esperado="38")],
        conclusiones=[Conclusion(variable_resultante_id=v_estado.id, valor_resultante="enfermo")],
    )
    r2 = Regla(
        nombre="R02",
        condiciones=[Condicion(variable_id=v_temp.id, operador=OperadorCondicion.MAYOR, valor_esperado="40")],
        conclusiones=[Conclusion(variable_resultante_id=v_estado.id, valor_resultante="sano")],
    )

    resultado = MotorValidacion.validar(uuid4(), [], [v_temp, v_estado], [r1, r2])
    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-012" in codigos
    inc = next(i for i in resultado.incidencias if i.codigo == "VAL-012")
    assert inc.severidad == SeveridadIncidencia.ERROR.value
    assert inc.tipo == "LOGICO"


def test_no_contradiccion_si_condiciones_son_disjuntas():
    """Reglas con rangos numéricos disjuntos (temp > 40 vs temp < 35) no generan conflicto VAL-012."""
    v_temp = Variable(nombre="temperatura", tipo_dato=TipoDato.DECIMAL)
    v_estado = Variable(nombre="estado", tipo_dato=TipoDato.TEXTO)

    r1 = Regla(
        nombre="R01",
        condiciones=[Condicion(variable_id=v_temp.id, operador=OperadorCondicion.MAYOR, valor_esperado="40")],
        conclusiones=[Conclusion(variable_resultante_id=v_estado.id, valor_resultante="fiebre_alta")],
    )
    r2 = Regla(
        nombre="R02",
        condiciones=[Condicion(variable_id=v_temp.id, operador=OperadorCondicion.MENOR, valor_esperado="35")],
        conclusiones=[Conclusion(variable_resultante_id=v_estado.id, valor_resultante="hipotermia")],
    )

    resultado = MotorValidacion.validar(uuid4(), [], [v_temp, v_estado], [r1, r2])
    assert not [i for i in resultado.incidencias if i.codigo == "VAL-012"]


def test_deteccion_contradiccion_indirecta_cadenas_val013():
    """
    VAL-013:
    R01: temp >= 38 -> tiene_fiebre = true
    R02: tiene_fiebre = true -> estado = enfermo
    R03: temp >= 38 -> estado = sano
    """
    v_temp = Variable(nombre="temperatura", tipo_dato=TipoDato.DECIMAL)
    v_fiebre = Variable(nombre="tiene_fiebre", tipo_dato=TipoDato.BOOLEANO)
    v_estado = Variable(nombre="estado", tipo_dato=TipoDato.TEXTO)

    r1 = Regla(
        nombre="R01",
        condiciones=[Condicion(variable_id=v_temp.id, operador=OperadorCondicion.MAYOR_IGUAL, valor_esperado="38")],
        conclusiones=[Conclusion(variable_resultante_id=v_fiebre.id, valor_resultante="true")],
    )
    r2 = Regla(
        nombre="R02",
        condiciones=[Condicion(variable_id=v_fiebre.id, operador=OperadorCondicion.IGUAL, valor_esperado="true")],
        conclusiones=[Conclusion(variable_resultante_id=v_estado.id, valor_resultante="enfermo")],
    )
    r3 = Regla(
        nombre="R03",
        condiciones=[Condicion(variable_id=v_temp.id, operador=OperadorCondicion.MAYOR_IGUAL, valor_esperado="38")],
        conclusiones=[Conclusion(variable_resultante_id=v_estado.id, valor_resultante="sano")],
    )

    resultado = MotorValidacion.validar(uuid4(), [], [v_temp, v_fiebre, v_estado], [r1, r2, r3])
    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-013" in codigos
    inc = next(i for i in resultado.incidencias if i.codigo == "VAL-013")
    assert inc.severidad == SeveridadIncidencia.ERROR.value
    assert inc.tipo == "LOGICO"


def test_deteccion_contradiccion_hecho_regla_val014():
    """VAL-014: Una regla concluye un valor que contradice un hecho inicial afirmado."""
    h_conexion = Hecho(nombre="conexion_internet", valor="true", tipo_dato=TipoDato.BOOLEANO, es_inicial=True)
    v_ping = Variable(nombre="ping_internet", tipo_dato=TipoDato.BOOLEANO)

    r1 = Regla(
        nombre="R_Corte",
        condiciones=[Condicion(variable_id=v_ping.id, operador=OperadorCondicion.IGUAL, valor_esperado="false")],
        conclusiones=[Conclusion(hecho_resultante_id=h_conexion.id, valor_resultante="false")],
    )

    resultado = MotorValidacion.validar(uuid4(), [h_conexion], [v_ping], [r1])
    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-014" in codigos
    inc = next(i for i in resultado.incidencias if i.codigo == "VAL-014")
    assert inc.severidad == SeveridadIncidencia.ERROR.value


def test_deteccion_condicion_imposible_val015():
    """VAL-015: Regla con condiciones mutuamente excluyentes (temp > 40 AND temp < 30)."""
    v_temp = Variable(nombre="temperatura", tipo_dato=TipoDato.DECIMAL)
    v_res = Variable(nombre="riesgo", tipo_dato=TipoDato.TEXTO)

    r1 = Regla(
        nombre="R_Imposible",
        condiciones=[
            Condicion(variable_id=v_temp.id, operador=OperadorCondicion.MAYOR, valor_esperado="40"),
            Condicion(variable_id=v_temp.id, operador=OperadorCondicion.MENOR, valor_esperado="30"),
        ],
        conclusiones=[Conclusion(variable_resultante_id=v_res.id, valor_resultante="alto")],
    )

    resultado = MotorValidacion.validar(uuid4(), [], [v_temp, v_res], [r1])
    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-015" in codigos
    inc = next(i for i in resultado.incidencias if i.codigo == "VAL-015")
    assert inc.severidad == SeveridadIncidencia.ERROR.value


def test_deteccion_condicion_imposible_booleana_val015():
    """VAL-015: Regla que exige activo = true AND activo = false."""
    h_activo = Hecho(nombre="activo", tipo_dato=TipoDato.BOOLEANO, es_inicial=True)
    v_res = Variable(nombre="resultado", tipo_dato=TipoDato.TEXTO)

    r1 = Regla(
        nombre="R_Bool_Imposible",
        condiciones=[
            Condicion(hecho_id=h_activo.id, operador=OperadorCondicion.IGUAL, valor_esperado="true"),
            Condicion(hecho_id=h_activo.id, operador=OperadorCondicion.IGUAL, valor_esperado="false"),
        ],
        conclusiones=[Conclusion(variable_resultante_id=v_res.id, valor_resultante="imposible")],
    )

    resultado = MotorValidacion.validar(uuid4(), [h_activo], [v_res], [r1])
    assert "VAL-015" in [i.codigo for i in resultado.incidencias]


def test_deteccion_valor_fuera_de_dominio_opcion_val017():
    """VAL-017: Regla asigna un valor que no pertenece a las opciones permitidas del hecho."""
    v_temp = Variable(nombre="temperatura", tipo_dato=TipoDato.DECIMAL)
    h_riesgo = Hecho(
        nombre="nivel_riesgo",
        tipo_dato=TipoDato.OPCION,
        opciones=["bajo", "medio", "alto"],
        es_inicial=False,
    )

    r1 = Regla(
        nombre="R_Dominio",
        condiciones=[Condicion(variable_id=v_temp.id, operador=OperadorCondicion.MAYOR, valor_esperado="40")],
        conclusiones=[Conclusion(hecho_resultante_id=h_riesgo.id, valor_resultante="extremo")],
    )

    resultado = MotorValidacion.validar(uuid4(), [h_riesgo], [v_temp], [r1])
    codigos = [inc.codigo for inc in resultado.incidencias]
    assert "VAL-017" in codigos
    inc = next(i for i in resultado.incidencias if i.codigo == "VAL-017")
    assert inc.severidad == SeveridadIncidencia.ERROR.value


@pytest.mark.django_db
def test_api_rest_deteccion_nuevas_inconsistencias_logicas(api_client, se_con_base):
    """Integración API: Validación de base con condiciones imposibles y contradicciones de dominio."""
    se, bc = se_con_base

    v_temp = CrearVariable().ejecutar(base_conocimiento_id=bc.id, nombre="Temperatura", tipo_dato="DECIMAL")
    h_riesgo = CrearHecho().ejecutar(
        base_conocimiento_id=bc.id, nombre="Nivel_Riesgo", tipo_dato="OPCION", opciones=["bajo", "alto"]
    )

    r1 = CrearRegla().ejecutar(base_conocimiento_id=bc.id, nombre="Regla_Riesgo_Critico", activa=True)
    AgregarCondicionARegla().ejecutar(
        regla_id=r1.id, variable_id=v_temp.id, operador=">", valor_esperado="40"
    )
    AgregarCondicionARegla().ejecutar(
        regla_id=r1.id, variable_id=v_temp.id, operador="<", valor_esperado="20"
    )
    AgregarConclusionARegla().ejecutar(
        regla_id=r1.id, hecho_resultante_id=h_riesgo.id, valor_resultante="critico_no_permitido"
    )

    url_val = reverse("validacion:base_conocimiento_validar", kwargs={"id": bc.id})
    resp = api_client.post(url_val)
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["data"]["es_valida"] is False
    assert resp.data["data"]["total_errores"] >= 2

    # Verificar reporte filtrado por tipo LOGICO
    val_id = resp.data["data"]["id"]
    url_inc = reverse("validacion:validacion_incidencias_list", kwargs={"id": val_id})
    resp_inc = api_client.get(f"{url_inc}?tipo=LOGICO")
    assert resp_inc.status_code == status.HTTP_200_OK
    codigos = [item["codigo"] for item in resp_inc.data["data"]]
    assert "VAL-015" in codigos
