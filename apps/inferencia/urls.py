"""
Enrutamiento de la API para el módulo de Inferencia.
"""
from django.urls import path
from apps.inferencia.views import (
    DetalleInferenciaListAPIView,
    EjecucionInferenciaDetailAPIView,
    InferenciaEjecutarAPIView,
)

app_name = "inferencia"

urlpatterns = [
    path(
        "sistemas-expertos/<uuid:id>/inferencias/",
        InferenciaEjecutarAPIView.as_view(),
        name="inferencia_ejecutar",
    ),
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
]
