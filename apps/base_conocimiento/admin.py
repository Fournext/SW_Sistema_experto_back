"""
Configuración del panel de administración de Django para Base de Conocimiento.
"""
from django.contrib import admin
from apps.base_conocimiento.models import (
    BaseConocimientoModel,
    ConclusionModel,
    CondicionModel,
    HechoModel,
    ReglaModel,
    VariableModel,
)


@admin.register(BaseConocimientoModel)
class BaseConocimientoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "version", "sistema_experto", "creada_en")
    search_fields = ("nombre",)
    readonly_fields = ("id", "creada_en", "actualizada_en")


@admin.register(HechoModel)
class HechoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "valor", "tipo_dato", "es_inicial", "base_conocimiento")
    list_filter = ("tipo_dato", "es_inicial")
    search_fields = ("nombre", "valor")


@admin.register(VariableModel)
class VariableAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "tipo_dato", "valor_defecto", "base_conocimiento")
    list_filter = ("tipo_dato",)
    search_fields = ("nombre",)


class CondicionInline(admin.TabularInline):
    model = CondicionModel
    extra = 1


class ConclusionInline(admin.TabularInline):
    model = ConclusionModel
    extra = 1


@admin.register(ReglaModel)
class ReglaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "prioridad", "factor_certeza", "activa", "base_conocimiento")
    list_filter = ("activa", "prioridad")
    search_fields = ("nombre", "descripcion")
    inlines = [CondicionInline, ConclusionInline]


@admin.register(CondicionModel)
class CondicionAdmin(admin.ModelAdmin):
    list_display = ("id", "regla", "operador", "valor_esperado", "orden")


@admin.register(ConclusionModel)
class ConclusionAdmin(admin.ModelAdmin):
    list_display = ("id", "regla", "valor_resultante")
