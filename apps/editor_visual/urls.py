"""
Enrutamiento de la API para el Editor Visual.
"""
from django.urls import path
from apps.editor_visual.views import (
    ConexionVisualCreateAPIView,
    ConexionVisualDetailAPIView,
    EditorVisualAPIView,
    NodoVisualCreateAPIView,
    NodoVisualDetailAPIView,
)

app_name = "editor_visual"

urlpatterns = [
    # Lienzo completo
    path(
        "sistemas-expertos/<uuid:id>/editor/",
        EditorVisualAPIView.as_view(),
        name="editor_visual",
    ),

    # Nodos
    path(
        "sistemas-expertos/<uuid:id>/nodos/",
        NodoVisualCreateAPIView.as_view(),
        name="nodo_visual_create",
    ),
    path(
        "nodos/<uuid:id>/",
        NodoVisualDetailAPIView.as_view(),
        name="nodo_visual_detail",
    ),

    # Conexiones
    path(
        "sistemas-expertos/<uuid:id>/conexiones/",
        ConexionVisualCreateAPIView.as_view(),
        name="conexion_visual_create",
    ),
    path(
        "conexiones/<uuid:id>/",
        ConexionVisualDetailAPIView.as_view(),
        name="conexion_visual_detail",
    ),
]
