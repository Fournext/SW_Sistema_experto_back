"""
Rutas de API REST para el módulo Laboratorio de Algoritmos.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AvanzarEjecucionAPIView,
    CompilarCodigoAPIView,
    IniciarEjecucionAPIView,
    PlantillasAlgoritmoAPIView,
    ProgramasAlgoritmoViewSet,
    ResponderPreguntaAPIView,
)

app_name = "laboratorio_algoritmos"

router = DefaultRouter()
router.register(r"laboratorio/programas", ProgramasAlgoritmoViewSet, basename="laboratorio-programas")

urlpatterns = [
    path("laboratorio/compilar/", CompilarCodigoAPIView.as_view(), name="laboratorio-compilar"),
    path("laboratorio/ejecutar/", IniciarEjecucionAPIView.as_view(), name="laboratorio-ejecutar"),
    path("laboratorio/corridas/<uuid:corrida_id>/avanzar/", AvanzarEjecucionAPIView.as_view(), name="laboratorio-avanzar"),
    path("laboratorio/corridas/<uuid:corrida_id>/responder/", ResponderPreguntaAPIView.as_view(), name="laboratorio-responder"),
    path("laboratorio/plantillas/", PlantillasAlgoritmoAPIView.as_view(), name="laboratorio-plantillas"),
    path("", include(router.urls)),
]

