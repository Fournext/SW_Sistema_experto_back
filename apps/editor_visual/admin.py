"""
Configuración del panel de administración de Django para Editor Visual.
"""
from django.contrib import admin
from apps.editor_visual.models import ConexionVisualModel, NodoVisualModel


@admin.register(NodoVisualModel)
class NodoVisualAdmin(admin.ModelAdmin):
    list_display = ("id", "sistema_experto", "tipo", "referencia_id", "posicion_x", "posicion_y")
    list_filter = ("tipo",)
    search_fields = ("referencia_id",)


@admin.register(ConexionVisualModel)
class ConexionVisualAdmin(admin.ModelAdmin):
    list_display = ("id", "sistema_experto", "nodo_origen", "nodo_destino", "etiqueta", "tipo")
    search_fields = ("etiqueta",)
