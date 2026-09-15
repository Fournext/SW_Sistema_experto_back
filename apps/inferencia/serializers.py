"""
Serializadores DRF para el módulo de Inferencia.
"""
from rest_framework import serializers


class HechoReporteSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    valor = serializers.JSONField()


class ReglaEvaluadaTrazaSerializer(serializers.Serializer):
    regla = serializers.CharField(source="regla_nombre")
    regla_id = serializers.UUIDField()
    estado = serializers.SerializerMethodField()
    condiciones_cumplidas = serializers.BooleanField(allow_null=True)
    orden = serializers.IntegerField()
    resultado_generado = serializers.CharField(allow_null=True, required=False)

    def get_estado(self, obj) -> str:
        val = getattr(obj, "estado", "")
        return val.value if hasattr(val, "value") else str(val)


class EjecutarInferenciaSalidaSerializer(serializers.Serializer):
    ejecucion_id = serializers.UUIDField()
    estado = serializers.SerializerMethodField()
    hechos_iniciales = HechoReporteSerializer(many=True)
    reglas_evaluadas = ReglaEvaluadaTrazaSerializer(many=True)
    hechos_generados = HechoReporteSerializer(many=True)
    conclusion_final = serializers.CharField(allow_null=True)

    def get_estado(self, obj) -> str:
        val = getattr(obj, "estado", "")
        return val.value if hasattr(val, "value") else str(val)


class EjecucionInferenciaSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sistema_experto_id = serializers.UUIDField(allow_null=True)
    estado = serializers.SerializerMethodField()
    fecha_inicio = serializers.DateTimeField(allow_null=True)
    fecha_fin = serializers.DateTimeField(allow_null=True)
    conclusion_final = serializers.CharField(allow_null=True)

    def get_estado(self, obj) -> str:
        val = getattr(obj, "estado", "")
        return val.value if hasattr(val, "value") else str(val)


class DetalleInferenciaSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    ejecucion_id = serializers.UUIDField(allow_null=True)
    regla_id = serializers.UUIDField(allow_null=True)
    orden = serializers.IntegerField()
    estado_regla = serializers.SerializerMethodField()
    condiciones_cumplidas = serializers.BooleanField(allow_null=True)
    resultado_generado = serializers.CharField(allow_null=True)

    def get_estado_regla(self, obj) -> str:
        val = getattr(obj, "estado_regla", "")
        return val.value if hasattr(val, "value") else str(val)
