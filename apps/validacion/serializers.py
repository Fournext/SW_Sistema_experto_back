"""
Serializadores DRF para el módulo de Validación de Bases de Conocimiento.
"""
from rest_framework import serializers


class IncidenciaValidacionSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    codigo = serializers.CharField()
    tipo = serializers.CharField()
    severidad = serializers.CharField()
    entidad_tipo = serializers.CharField()
    entidad_id = serializers.UUIDField(allow_null=True)
    entidad_nombre = serializers.CharField(allow_null=True)
    descripcion = serializers.CharField()
    posible_causa = serializers.CharField()
    sugerencia = serializers.CharField()
    creada_en = serializers.DateTimeField(allow_null=True)


class ValidacionBaseSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    base_conocimiento_id = serializers.UUIDField()
    fecha_validacion = serializers.DateTimeField(allow_null=True)
    es_valida = serializers.BooleanField()
    total_errores = serializers.IntegerField()
    total_advertencias = serializers.IntegerField()
    resumen = serializers.CharField()
    incidencias = IncidenciaValidacionSalidaSerializer(many=True)
