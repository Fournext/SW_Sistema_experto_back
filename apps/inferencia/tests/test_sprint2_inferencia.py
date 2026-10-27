"""
Pruebas unitarias y de integración para las historias de usuario de Inferencia y Simulación (Sprint 2):
- HU-09: Ejecutar inferencia paso a paso
- HU-12: Visualizar hechos generados
- HU-13: Visualizar conflictos
- HU-14: Simular sistema experto
- HU-15: Controlar simulación
- HU-16: Consultar historial de inferencia
- HU-17: Explicar conclusión
"""
import pytest
from uuid import uuid4
from django.urls import reverse
from rest_framework import status

from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import (
    AgregarConclusionARegla,
    AgregarCondicionARegla,
    CrearHecho,
    CrearRegla,
    CrearVariable,
)
from apps.inferencia.conflict_resolution import ResolucionPorPrioridad
from apps.inferencia.engine import MotorInferencia
from apps.inferencia.explicabilidad import MotorExplicabilidad
from apps.inferencia.services import (
    AvanzarPasoSimulacion,
    ConsultarConflictosEjecucion,
    ConsultarExplicacionConclusion,
    ConsultarHechosInferidos,
    ConsultarHistorialInferencia,
    ControlarSimulacion,
    EjecutarInferencia,
    IniciarSimulacion,
)
from apps.sistemas_expertos.services import CrearSistemaExperto
from compartido.constantes.enums import EstadoEjecucion, ModoInferencia, OperadorCondicion, TipoDato


@pytest.fixture
def se_simulacion_completo(db):
    """Fixture que crea un SE con hechos, variables y 2 reglas en conflicto por prioridad."""
    se = CrearSistemaExperto().ejecutar(nombre="SE Medico Diagnostico")
    bc = BaseConocimientoModel.objects.get(sistema_experto_id=se.id)

    # Hechos iniciales
    h_temp = CrearHecho().ejecutar(
        base_conocimiento_id=bc.id,
        nombre="temperatura_alta",
        valor="true",
        tipo_dato=TipoDato.BOOLEANO,
    )
    h_tos = CrearHecho().ejecutar(
        base_conocimiento_id=bc.id,
        nombre="tiene_tos",
        valor="true",
        tipo_dato=TipoDato.BOOLEANO,
    )

    # Variable resultante
    v_diag = CrearVariable().ejecutar(
        base_conocimiento_id=bc.id,
        nombre="diagnostico",
        tipo_dato=TipoDato.TEXTO,
    )

    # Regla 1 (Prioridad 10 - Gripe)
    r_gripe = CrearRegla().ejecutar(
        base_conocimiento_id=bc.id,
        nombre="Regla Gripe Fuerte",
        prioridad=10,
        activa=True,
    )
    AgregarCondicionARegla().ejecutar(
        regla_id=r_gripe.id,
        hecho_id=h_temp.id,
        operador="=",
        valor_esperado="true",
        orden=1,
    )
    AgregarCondicionARegla().ejecutar(
        regla_id=r_gripe.id,
        hecho_id=h_tos.id,
        operador="=",
        valor_esperado="true",
        orden=2,
    )
    AgregarConclusionARegla().ejecutar(
        regla_id=r_gripe.id,
        variable_resultante_id=v_diag.id,
        valor_resultante="Gripe Fuerte",
    )

    # Regla 2 (Prioridad 5 - Resfriado común, en conflicto con Regla 1)
    r_resfriado = CrearRegla().ejecutar(
        base_conocimiento_id=bc.id,
        nombre="Regla Resfriado Comun",
        prioridad=5,
        activa=True,
    )
    AgregarCondicionARegla().ejecutar(
        regla_id=r_resfriado.id,
        hecho_id=h_tos.id,
        operador="=",
        valor_esperado="true",
        orden=1,
    )
    AgregarConclusionARegla().ejecutar(
        regla_id=r_resfriado.id,
        variable_resultante_id=v_diag.id,
        valor_resultante="Resfriado Comun",
    )

    return se, bc, [h_temp, h_tos], [v_diag]


@pytest.mark.django_db
def test_motor_ejecutar_un_paso_incremental(se_simulacion_completo):
    """HU-09: El motor permite evaluar y avanzar un único paso incrementalmente."""
    se, bc, hechos, variables = se_simulacion_completo
    from apps.base_conocimiento.repositories import DjangoReglaRepositorio
    reglas = DjangoReglaRepositorio().listar_activas_por_base(bc.id)
    motor = MotorInferencia()
    mapa_ids = MotorInferencia.construir_mapa_ids(hechos, reglas, variables)

    memoria = {"temperatura_alta": True, "tiene_tos": True}
    reglas_ejecutadas = set()

    # Paso 1: Hay conflicto entre Regla Gripe (P=10) y Regla Resfriado (P=5)
    paso_1 = motor.ejecutar_un_paso(
        memoria_trabajo=memoria,
        reglas_ejecutadas=reglas_ejecutadas,
        reglas=reglas,
        variables=variables,
        mapa_ids_a_nombres=mapa_ids,
        numero_paso=1,
    )

    assert not paso_1.finalizado
    assert paso_1.regla_disparada.nombre == "Regla Gripe Fuerte"
    assert len(paso_1.candidatas_conflicto) == 2
    assert paso_1.memoria_trabajo_post["diagnostico"] == "Gripe Fuerte"
    assert paso_1.hechos_generados[0]["nombre"] == "diagnostico"
    assert paso_1.hechos_generados[0]["valor"] == "Gripe Fuerte"

    # Paso 2: Con la regla ganadora marcada como ejecutada
    reglas_ejecutadas.add(paso_1.regla_disparada.id)
    paso_2 = motor.ejecutar_un_paso(
        memoria_trabajo=paso_1.memoria_trabajo_post,
        reglas_ejecutadas=reglas_ejecutadas,
        reglas=reglas,
        variables=variables,
        mapa_ids_a_nombres=mapa_ids,
        numero_paso=2,
    )
    assert not paso_2.finalizado
    assert paso_2.regla_disparada.nombre == "Regla Resfriado Comun"

    # Paso 3: Ya no quedan reglas
    reglas_ejecutadas.add(paso_2.regla_disparada.id)
    paso_3 = motor.ejecutar_un_paso(
        memoria_trabajo=paso_2.memoria_trabajo_post,
        reglas_ejecutadas=reglas_ejecutadas,
        reglas=reglas,
        variables=variables,
        mapa_ids_a_nombres=mapa_ids,
        numero_paso=3,
    )
    assert paso_3.finalizado


@pytest.mark.django_db
def test_resolucion_conflictos_detallada_y_determinista(se_simulacion_completo):
    """HU-13: Verificación de conjunto de conflicto, selección por prioridad y motivos de descarte."""
    se, bc, _, _ = se_simulacion_completo
    from apps.base_conocimiento.repositories import DjangoReglaRepositorio
    reglas = DjangoReglaRepositorio().listar_activas_por_base(bc.id)
    estrategia = ResolucionPorPrioridad()
    resultado = estrategia.resolver_con_detalle(reglas)

    assert resultado.regla_ganadora.nombre == "Regla Gripe Fuerte"
    assert resultado.regla_ganadora.prioridad == 10
    descarte_resfriado = [m for rid, m in resultado.motivos_descarte.items()]
    assert any("Menor prioridad" in m for m in descarte_resfriado)


@pytest.mark.django_db
def test_simulacion_iniciar_y_paso_a_paso(se_simulacion_completo):
    """HU-14 y HU-15: Iniciar simulación con hechos personalizados y avanzar paso a paso."""
    se, bc, _, _ = se_simulacion_completo

    # Hechos personalizados que no alteran la base persistente
    hechos_custom = [
        {"nombre": "temperatura_alta", "valor": "false", "tipo_dato": "BOOLEANO"},
        {"nombre": "tiene_tos", "valor": "true", "tipo_dato": "BOOLEANO"},
    ]

    iniciar_service = IniciarSimulacion()
    ejecucion = iniciar_service.ejecutar(se.id, hechos_iniciales_custom=hechos_custom)

    assert ejecucion.es_simulacion
    assert ejecucion.modo == ModoInferencia.SIMULACION
    assert ejecucion.estado == EstadoEjecucion.INICIADA
    assert ejecucion.paso_actual == 0

    # Avanzar paso 1: Solo Regla Resfriado debe activarse porque temperatura_alta es false
    avanzar_service = AvanzarPasoSimulacion()
    res_paso = avanzar_service.ejecutar(ejecucion.id)

    assert not res_paso["finalizado"]
    assert res_paso["memoria_trabajo"]["diagnostico"] == "Resfriado Comun"

    # Consultar hechos inferidos (HU-12)
    hechos_service = ConsultarHechosInferidos()
    hechos_inf = hechos_service.ejecutar(ejecucion.id)
    assert len(hechos_inf) >= 1
    assert any(h.nombre == "diagnostico" and h.valor == "Resfriado Comun" for h in hechos_inf)

    # Avanzar paso 2: Finaliza
    res_paso_2 = avanzar_service.ejecutar(ejecucion.id)
    assert res_paso_2["finalizado"]


@pytest.mark.django_db
def test_simulacion_pausar_reiniciar_y_continuar(se_simulacion_completo):
    """HU-15: Transiciones de control de simulación (pausar, reiniciar, continuar)."""
    se, bc, _, _ = se_simulacion_completo
    iniciar_service = IniciarSimulacion()
    ejecucion = iniciar_service.ejecutar(se.id)

    control_service = ControlarSimulacion()
    # Pausar
    ejecucion_pausada = control_service.pausar(ejecucion.id)
    assert ejecucion_pausada.estado == EstadoEjecucion.PAUSADA

    # Reiniciar
    ejecucion_reiniciada = control_service.reiniciar(ejecucion.id)
    assert ejecucion_reiniciada.estado == EstadoEjecucion.INICIADA
    assert ejecucion_reiniciada.paso_actual == 0

    # Continuar
    ejecucion_fin = control_service.continuar(ejecucion.id)
    assert ejecucion_fin.estado == EstadoEjecucion.FINALIZADA
    assert ejecucion_fin.conclusion_final is not None


@pytest.mark.django_db
def test_explicabilidad_determinista_conclusion(se_simulacion_completo):
    """HU-17: Generación de árbol causal de explicación sin LLMs."""
    se, bc, _, _ = se_simulacion_completo
    ejecutar_service = EjecutarInferencia()
    resultado = ejecutar_service.ejecutar(se.id)

    explicar_service = ConsultarExplicacionConclusion()
    explicacion = explicar_service.ejecutar(resultado.ejecucion_id)

    assert "conclusion" in explicacion
    assert explicacion["conclusion"] is not None
    assert "arbol" in explicacion
    assert explicacion["arbol"]["tipo"] == "CADENA_CAUSAL"
    assert "Regla Gripe Fuerte" in explicacion["texto"]


@pytest.mark.django_db
def test_historial_inferencia_filtros(se_simulacion_completo):
    """HU-16: Consulta de historial de inferencias con filtros."""
    se, bc, _, _ = se_simulacion_completo
    ejecutar_service = EjecutarInferencia()
    ejecutar_service.ejecutar(se.id)

    iniciar_service = IniciarSimulacion()
    iniciar_service.ejecutar(se.id)

    historial_service = ConsultarHistorialInferencia()
    todas = historial_service.ejecutar(sistema_experto_id=se.id)
    assert len(todas) >= 2

    solo_simulaciones = historial_service.ejecutar(
        sistema_experto_id=se.id, modo=ModoInferencia.SIMULACION.value
    )
    assert len(solo_simulaciones) >= 1
    assert all(e.modo == ModoInferencia.SIMULACION for e in solo_simulaciones)


@pytest.mark.django_db
def test_api_rest_simulacion_endpoints(api_client, se_simulacion_completo):
    """Verificación de endpoints REST para simulación y navegación paso a paso."""
    se, bc, _, _ = se_simulacion_completo

    # 1. Iniciar simulación por API
    url_iniciar = reverse("inferencia:simulacion_iniciar", kwargs={"id": se.id})
    resp = api_client.post(
        url_iniciar,
        data={
            "hechos_iniciales": [
                {"nombre": "temperatura_alta", "valor": "true"},
                {"nombre": "tiene_tos", "valor": "true"},
            ]
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    ejecucion_id = resp.data["data"]["id"]

    # 2. Avanzar paso por API
    url_paso = reverse("inferencia:simulacion_avanzar_paso", kwargs={"id": ejecucion_id})
    resp_paso = api_client.post(url_paso)
    assert resp_paso.status_code == status.HTTP_200_OK
    assert "memoria_trabajo" in resp_paso.data["data"]

    # 3. Consultar hechos inferidos por API (HU-12)
    url_hechos = reverse("inferencia:inferencia_hechos_inferidos", kwargs={"id": ejecucion_id})
    resp_hechos = api_client.get(url_hechos)
    assert resp_hechos.status_code == status.HTTP_200_OK

    # 4. Consultar conflictos por API (HU-13)
    url_conf = reverse("inferencia:inferencia_conflictos", kwargs={"id": ejecucion_id})
    resp_conf = api_client.get(url_conf)
    assert resp_conf.status_code == status.HTTP_200_OK

    # 5. Pausar y reiniciar por API (HU-15)
    url_pausa = reverse("inferencia:simulacion_pausar", kwargs={"id": ejecucion_id})
    resp_pausa = api_client.post(url_pausa)
    assert resp_pausa.status_code == status.HTTP_200_OK
    assert resp_pausa.data["data"]["estado"] == "PAUSADA"

    url_reiniciar = reverse("inferencia:simulacion_reiniciar", kwargs={"id": ejecucion_id})
    resp_reiniciar = api_client.post(url_reiniciar)
    assert resp_reiniciar.status_code == status.HTTP_200_OK
    assert resp_reiniciar.data["data"]["estado"] == "INICIADA"

    # 6. Historial de inferencias (HU-16)
    url_hist = reverse("inferencia:inferencia_historial")
    resp_hist = api_client.get(f"{url_hist}?sistema_id={se.id}")
    assert resp_hist.status_code == status.HTTP_200_OK
    assert len(resp_hist.data["data"]) >= 1

    # 7. Explicación de conclusión (HU-17)
    url_expl = reverse("inferencia:inferencia_explicacion", kwargs={"id": ejecucion_id})
    resp_expl = api_client.get(url_expl)
    assert resp_expl.status_code == status.HTTP_200_OK
    assert "arbol" in resp_expl.data["data"]

    # 8. Verificación de rutas alias usadas por el frontend
    url_iniciar_alias = reverse("inferencia:simulacion_iniciar_alias", kwargs={"id": se.id})
    resp_init_alias = api_client.post(url_iniciar_alias, {"hechos_iniciales": []}, format="json")
    assert resp_init_alias.status_code == status.HTTP_201_CREATED
    alias_id = resp_init_alias.data["data"]["id"]

    url_paso_alias = reverse("inferencia:simulaciones_avanzar_paso_alias", kwargs={"id": alias_id})
    resp_paso_alias = api_client.post(url_paso_alias)
    assert resp_paso_alias.status_code == status.HTTP_200_OK

    url_control = reverse("inferencia:simulacion_control", kwargs={"id": alias_id})
    resp_ctrl = api_client.post(url_control, {"accion": "PAUSAR"}, format="json")
    assert resp_ctrl.status_code == status.HTTP_200_OK
    assert resp_ctrl.data["data"]["estado"] == "PAUSADA"
