"""
Serializadores DRF para el módulo de Sistemas Expertos.
"""
from rest_framework import serializers
from compartido.constantes.enums import EstadoSistema


class SistemaExpertoEntradaSerializer(serializers.Serializer):
    """Valida los datos de entrada para crear o actualizar un Sistema Experto."""

    nombre = serializers.CharField(
        max_length=150,
        required=True,
        error_messages={"required": "El campo 'nombre' es obligatorio."},
    )
    descripcion = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    estado = serializers.ChoiceField(
        choices=EstadoSistema.choices(),
        default=EstadoSistema.BORRADOR.value,
        required=False,
    )


class SistemaExpertoParcialEntradaSerializer(serializers.Serializer):
    """Valida datos de actualización parcial (PATCH)."""

    nombre = serializers.CharField(max_length=150, required=False)
    descripcion = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    estado = serializers.ChoiceField(choices=EstadoSistema.choices(), required=False)


class SistemaExpertoSalidaSerializer(serializers.Serializer):
    """Representa la respuesta de un Sistema Experto hacia el cliente."""

    id = serializers.UUIDField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField(allow_null=True)
    estado = serializers.CharField()
    creado_en = serializers.DateTimeField(allow_null=True)
    actualizado_en = serializers.DateTimeField(allow_null=True)
