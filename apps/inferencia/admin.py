"""
Configuración del panel de administración de Django para Inferencia.
"""
from django.contrib import admin
from apps.inferencia.models import DetalleInferenciaModel, EjecucionInferenciaModel


class DetalleInferenciaInline(admin.TabularInline):
    model = DetalleInferenciaModel
    extra = 0
    readonly_fields = (
        "orden",
        "regla",
        "estado_regla",
        "condiciones_cumplidas",
        "resultado_generado",
    )


@admin.register(EjecucionInferenciaModel)
class EjecucionInferenciaAdmin(admin.ModelAdmin):
    list_display = ("id", "sistema_experto", "estado", "fecha_inicio", "fecha_fin", "conclusion_final")
    list_filter = ("estado", "fecha_inicio")
    readonly_fields = ("id", "fecha_inicio", "fecha_fin")
    inlines = [DetalleInferenciaInline]


@admin.register(DetalleInferenciaModel)
class DetalleInferenciaAdmin(admin.ModelAdmin):
    list_display = ("id", "ejecucion", "regla", "orden", "estado_regla", "condiciones_cumplidas")
    list_filter = ("estado_regla",)
