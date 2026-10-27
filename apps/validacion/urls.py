"""
Enrutamiento de la API para el módulo de Validación de Bases de Conocimiento.
"""
from django.urls import path
from apps.validacion.views import (
    BaseConocimientoValidarAPIView,
    IncidenciasListAPIView,
    UltimaValidacionAPIView,
    ValidacionDetailAPIView,
)

app_name = "validacion"

urlpatterns = [
    # Ejecutar validación sobre una base de conocimiento
    path(
        "bases-conocimiento/<uuid:id>/validar/",
        BaseConocimientoValidarAPIView.as_view(),
        name="base_conocimiento_validar",
    ),
    # Consultar última validación de una base
    path(
        "bases-conocimiento/<uuid:id>/validaciones/ultima/",
        UltimaValidacionAPIView.as_view(),
        name="base_conocimiento_ultima_validacion",
    ),
    # Consultar validación específica por ID
    path(
        "validaciones/<uuid:id>/",
        ValidacionDetailAPIView.as_view(),
        name="validacion_detail",
    ),
    # Consultar reporte de incidencias de una validación
    path(
        "validaciones/<uuid:id>/incidencias/",
        IncidenciasListAPIView.as_view(),
        name="validacion_incidencias_list",
    ),
]
