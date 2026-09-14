"""
Enrutamiento de la API para Base de Conocimiento (Hechos, Variables, Reglas, Condiciones, Conclusiones).
"""
from django.urls import path
from apps.base_conocimiento.views import (
    BaseConocimientoPorSistemaAPIView,
    ConclusionCreateAPIView,
    ConclusionDetailAPIView,
    CondicionCreateAPIView,
    CondicionDetailAPIView,
    HechoDetailAPIView,
    HechoListCreateAPIView,
    ReglaDetailAPIView,
    ReglaListCreateAPIView,
    VariableDetailAPIView,
    VariableListCreateAPIView,
)

app_name = "base_conocimiento"

urlpatterns = [
    # Base de conocimiento
    path(
        "sistemas-expertos/<uuid:id>/base-conocimiento/",
        BaseConocimientoPorSistemaAPIView.as_view(),
        name="base_conocimiento_por_sistema",
    ),

    # Hechos
    path("bases-conocimiento/<uuid:id>/hechos/", HechoListCreateAPIView.as_view(), name="hecho_list_create"),
    path("hechos/<uuid:id>/", HechoDetailAPIView.as_view(), name="hecho_detail"),

    # Variables
    path("bases-conocimiento/<uuid:id>/variables/", VariableListCreateAPIView.as_view(), name="variable_list_create"),
    path("variables/<uuid:id>/", VariableDetailAPIView.as_view(), name="variable_detail"),

    # Reglas
    path("bases-conocimiento/<uuid:id>/reglas/", ReglaListCreateAPIView.as_view(), name="regla_list_create"),
    path("reglas/<uuid:id>/", ReglaDetailAPIView.as_view(), name="regla_detail"),

    # Condiciones
    path("reglas/<uuid:id>/condiciones/", CondicionCreateAPIView.as_view(), name="condicion_create"),
    path("condiciones/<uuid:id>/", CondicionDetailAPIView.as_view(), name="condicion_detail"),

    # Conclusiones
    path("reglas/<uuid:id>/conclusiones/", ConclusionCreateAPIView.as_view(), name="conclusion_create"),
    path("conclusiones/<uuid:id>/", ConclusionDetailAPIView.as_view(), name="conclusion_detail"),
]
