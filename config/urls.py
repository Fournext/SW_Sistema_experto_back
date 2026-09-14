"""
Enrutador principal de URLs para el proyecto de Software Educativo de Sistemas Expertos.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Documentación Swagger / OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Rutas API v1 por módulo
    path("api/v1/", include("apps.sistemas_expertos.urls", namespace="sistemas_expertos")),
    path("api/v1/", include("apps.base_conocimiento.urls", namespace="base_conocimiento")),
    path("api/v1/", include("apps.editor_visual.urls", namespace="editor_visual")),
    path("api/v1/", include("apps.inferencia.urls", namespace="inferencia")),
]
