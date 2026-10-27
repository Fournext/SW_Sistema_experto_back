"""
Enrutamiento de la API para el módulo de Inferencia y Simulación (Sprint 1 + Sprint 2).
"""
from django.urls import path
from apps.inferencia.views import (
    DetalleInferenciaListAPIView,
    EjecucionInferenciaDetailAPIView,
    InferenciaConflictosListAPIView,
    InferenciaEjecutarAPIView,
    InferenciaExplicacionDetailAPIView,
    InferenciaHechosInferidosListAPIView,
    InferenciaHistorialAPIView,
    PasoInferenciaListAPIView,
    SimulacionAvanzarPasoAPIView,
    SimulacionContinuarAPIView,
    SimulacionControlAPIView,
    SimulacionFinalizarAPIView,
    SimulacionIniciarAPIView,
    SimulacionPausarAPIView,
    SimulacionReiniciarAPIView,
)

app_name = "inferencia"

urlpatterns = [
    # Historial general
    path(
        "inferencias/",
        InferenciaHistorialAPIView.as_view(),
        name="inferencia_historial",
    ),
    path(
        "historial-inferencias/",
        InferenciaHistorialAPIView.as_view(),
        name="historial_inferencias_alias",
    ),

    # Inferencia automática
    path(
        "sistemas-expertos/<uuid:id>/inferencias/",
        InferenciaEjecutarAPIView.as_view(),
        name="inferencia_ejecutar",
    ),

    # Iniciar simulación interactiva (soporta /simulaciones/ y /simulaciones/iniciar/)
    path(
        "sistemas-expertos/<uuid:id>/simulaciones/",
        SimulacionIniciarAPIView.as_view(),
        name="simulacion_iniciar",
    ),
    path(
        "sistemas-expertos/<uuid:id>/simulaciones/iniciar/",
        SimulacionIniciarAPIView.as_view(),
        name="simulacion_iniciar_alias",
    ),

    # Consultas sobre una ejecución específica
    path(
        "inferencias/<uuid:id>/",
        EjecucionInferenciaDetailAPIView.as_view(),
        name="ejecucion_inferencia_detail",
    ),
    path(
        "inferencias/<uuid:id>/detalles/",
        DetalleInferenciaListAPIView.as_view(),
        name="detalle_inferencia_list",
    ),
    path(
        "inferencias/<uuid:id>/pasos/",
        PasoInferenciaListAPIView.as_view(),
        name="paso_inferencia_list",
    ),

    # Hechos inferidos (soporta /inferencias/ y /ejecuciones/)
    path(
        "inferencias/<uuid:id>/hechos-inferidos/",
        InferenciaHechosInferidosListAPIView.as_view(),
        name="inferencia_hechos_inferidos",
    ),
    path(
        "ejecuciones/<uuid:id>/hechos-inferidos/",
        InferenciaHechosInferidosListAPIView.as_view(),
        name="ejecuciones_hechos_inferidos_alias",
    ),

    # Conflictos (soporta /inferencias/ y /ejecuciones/)
    path(
        "inferencias/<uuid:id>/conflictos/",
        InferenciaConflictosListAPIView.as_view(),
        name="inferencia_conflictos",
    ),
    path(
        "ejecuciones/<uuid:id>/conflictos/",
        InferenciaConflictosListAPIView.as_view(),
        name="ejecuciones_conflictos_alias",
    ),

    # Explicación (soporta /inferencias/ y /ejecuciones/)
    path(
        "inferencias/<uuid:id>/explicacion/",
        InferenciaExplicacionDetailAPIView.as_view(),
        name="inferencia_explicacion",
    ),
    path(
        "ejecuciones/<uuid:id>/explicacion/",
        InferenciaExplicacionDetailAPIView.as_view(),
        name="ejecuciones_explicacion_alias",
    ),

    # Controles de simulación paso a paso (soporta /inferencias/ y /simulaciones/)
    path(
        "inferencias/<uuid:id>/paso/",
        SimulacionAvanzarPasoAPIView.as_view(),
        name="simulacion_avanzar_paso",
    ),
    path(
        "simulaciones/<uuid:id>/paso/",
        SimulacionAvanzarPasoAPIView.as_view(),
        name="simulaciones_avanzar_paso_alias",
    ),

    # Control unificado de ciclo de vida
    path(
        "simulaciones/<uuid:id>/control/",
        SimulacionControlAPIView.as_view(),
        name="simulacion_control",
    ),
    path(
        "inferencias/<uuid:id>/control/",
        SimulacionControlAPIView.as_view(),
        name="inferencia_control_alias",
    ),

    # Endpoints individuales de control
    path(
        "inferencias/<uuid:id>/pausar/",
        SimulacionPausarAPIView.as_view(),
        name="simulacion_pausar",
    ),
    path(
        "simulaciones/<uuid:id>/pausar/",
        SimulacionPausarAPIView.as_view(),
        name="simulacion_pausar_alias",
    ),
    path(
        "inferencias/<uuid:id>/continuar/",
        SimulacionContinuarAPIView.as_view(),
        name="simulacion_continuar",
    ),
    path(
        "simulaciones/<uuid:id>/continuar/",
        SimulacionContinuarAPIView.as_view(),
        name="simulacion_continuar_alias",
    ),
    path(
        "inferencias/<uuid:id>/reiniciar/",
        SimulacionReiniciarAPIView.as_view(),
        name="simulacion_reiniciar",
    ),
    path(
        "simulaciones/<uuid:id>/reiniciar/",
        SimulacionReiniciarAPIView.as_view(),
        name="simulacion_reiniciar_alias",
    ),
    path(
        "inferencias/<uuid:id>/finalizar/",
        SimulacionFinalizarAPIView.as_view(),
        name="simulacion_finalizar",
    ),
    path(
        "simulaciones/<uuid:id>/finalizar/",
        SimulacionFinalizarAPIView.as_view(),
        name="simulacion_finalizar_alias",
    ),
]
