"""
Serializadores DRF para el módulo de Editor Visual.
"""
from rest_framework import serializers
from compartido.constantes.enums import TipoNodoVisual


class NodoVisualEntradaSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=TipoNodoVisual.choices())
    referencia_id = serializers.UUIDField()
    posicion_x = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    posicion_y = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.0)


class NodoVisualMoverEntradaSerializer(serializers.Serializer):
    posicion_x = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    posicion_y = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)


class NodoVisualSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sistema_experto_id = serializers.UUIDField(allow_null=True)
    tipo = serializers.CharField()
    referencia_id = serializers.UUIDField()
    posicion_x = serializers.DecimalField(max_digits=10, decimal_places=2)
    posicion_y = serializers.DecimalField(max_digits=10, decimal_places=2)


class ConexionVisualEntradaSerializer(serializers.Serializer):
    nodo_origen_id = serializers.UUIDField()
    nodo_destino_id = serializers.UUIDField()
    etiqueta = serializers.CharField(
        max_length=100, required=False, allow_null=True, allow_blank=True
    )
    tipo = serializers.CharField(
        max_length=50, required=False, allow_null=True, allow_blank=True
    )


class ConexionVisualSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sistema_experto_id = serializers.UUIDField(allow_null=True)
    nodo_origen_id = serializers.UUIDField()
    nodo_destino_id = serializers.UUIDField()
    etiqueta = serializers.CharField(allow_null=True)
    tipo = serializers.CharField(allow_null=True)


class EditorVisualSalidaSerializer(serializers.Serializer):
    sistema_experto_id = serializers.UUIDField()
    nodos = NodoVisualSalidaSerializer(many=True)
    conexiones = ConexionVisualSalidaSerializer(many=True)
