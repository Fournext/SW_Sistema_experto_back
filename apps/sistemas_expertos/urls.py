"""
Enrutamiento de la API para Sistemas Expertos.
"""
from django.urls import path
from apps.sistemas_expertos.views import (
    SistemaExpertoListCreateAPIView,
    SistemaExpertoDetailAPIView,
)

app_name = "sistemas_expertos"

urlpatterns = [
    path("sistemas-expertos/", SistemaExpertoListCreateAPIView.as_view(), name="sistema_experto_list_create"),
    path("sistemas-expertos/<uuid:id>/", SistemaExpertoDetailAPIView.as_view(), name="sistema_experto_detail"),
]
