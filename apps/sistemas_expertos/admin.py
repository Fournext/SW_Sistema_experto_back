"""
Configuración del panel de administración de Django para Sistemas Expertos.
"""
from django.contrib import admin
from apps.sistemas_expertos.models import SistemaExpertoModel


@admin.register(SistemaExpertoModel)
class SistemaExpertoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "estado", "creado_en", "actualizado_en")
    list_filter = ("estado", "creado_en")
    search_fields = ("nombre", "descripcion")
    readonly_fields = ("id", "creado_en", "actualizado_en")
