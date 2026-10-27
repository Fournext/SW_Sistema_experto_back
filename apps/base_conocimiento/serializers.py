"""
Serializadores DRF para el módulo de Base de Conocimiento.
"""
from decimal import Decimal
from rest_framework import serializers
from compartido.constantes.enums import OperadorCondicion, TipoDato


# =====================================================================
# CONDICION SERIALIZERS
# =====================================================================

class CondicionEntradaSerializer(serializers.Serializer):
    operador = serializers.ChoiceField(choices=OperadorCondicion.choices())
    valor_esperado = serializers.CharField(max_length=255)
    variable_id = serializers.UUIDField(required=False, allow_null=True)
    hecho_id = serializers.UUIDField(required=False, allow_null=True)
    orden = serializers.IntegerField(default=1, min_value=1)

    def validate(self, attrs):
        var_id = attrs.get("variable_id")
        hecho_id = attrs.get("hecho_id")
        if not ((var_id is not None) ^ (hecho_id is not None)):
            raise serializers.ValidationError(
                "Debe especificar exactamente uno entre 'variable_id' y 'hecho_id'."
            )
        return attrs


class CondicionParcialEntradaSerializer(serializers.Serializer):
    operador = serializers.ChoiceField(choices=OperadorCondicion.choices(), required=False)
    valor_esperado = serializers.CharField(max_length=255, required=False)
    variable_id = serializers.UUIDField(required=False, allow_null=True)
    hecho_id = serializers.UUIDField(required=False, allow_null=True)
    orden = serializers.IntegerField(min_value=1, required=False)


class CondicionSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    regla_id = serializers.UUIDField(allow_null=True)
    variable_id = serializers.UUIDField(allow_null=True)
    hecho_id = serializers.UUIDField(allow_null=True)
    operador = serializers.CharField()
    valor_esperado = serializers.CharField()
    orden = serializers.IntegerField()


# =====================================================================
# CONCLUSION SERIALIZERS
# =====================================================================

class ConclusionEntradaSerializer(serializers.Serializer):
    valor_resultante = serializers.CharField(max_length=255)
    hecho_resultante_id = serializers.UUIDField(required=False, allow_null=True)
    variable_resultante_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        h_id = attrs.get("hecho_resultante_id")
        v_id = attrs.get("variable_resultante_id")
        if not ((h_id is not None) ^ (v_id is not None)):
            raise serializers.ValidationError(
                "Debe especificar exactamente uno entre 'hecho_resultante_id' y 'variable_resultante_id'."
            )
        return attrs


class ConclusionParcialEntradaSerializer(serializers.Serializer):
    valor_resultante = serializers.CharField(max_length=255, required=False)
    hecho_resultante_id = serializers.UUIDField(required=False, allow_null=True)
    variable_resultante_id = serializers.UUIDField(required=False, allow_null=True)


class ConclusionSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    regla_id = serializers.UUIDField(allow_null=True)
    hecho_resultante_id = serializers.UUIDField(allow_null=True)
    variable_resultante_id = serializers.UUIDField(allow_null=True)
    valor_resultante = serializers.CharField()


# =====================================================================
# HECHO SERIALIZERS
# =====================================================================

class ValorInicialField(serializers.CharField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            return "true" if data else "false"
        return super().to_internal_value(data)


class HechoEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150, required=True)
    valor = ValorInicialField(max_length=255, required=False, allow_null=True, allow_blank=True)
    tipo_dato = serializers.ChoiceField(choices=TipoDato.choices(), default=TipoDato.TEXTO.value)
    opciones = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
        default=list,
    )
    pregunta = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )
    es_inicial = serializers.BooleanField(default=True)


class HechoParcialEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150, required=False)
    valor = ValorInicialField(max_length=255, required=False, allow_null=True, allow_blank=True)
    tipo_dato = serializers.ChoiceField(choices=TipoDato.choices(), required=False)
    opciones = serializers.ListField(
        child=serializers.CharField(max_length=150),
        required=False,
    )
    pregunta = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )
    es_inicial = serializers.BooleanField(required=False)


class HechoSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    base_conocimiento_id = serializers.UUIDField(allow_null=True)
    nombre = serializers.CharField()
    valor = serializers.CharField(allow_null=True)
    tipo_dato = serializers.CharField()
    opciones = serializers.ListField(child=serializers.CharField(), default=list)
    pregunta = serializers.CharField(allow_null=True)
    es_inicial = serializers.BooleanField()


# =====================================================================
# VARIABLE SERIALIZERS
# =====================================================================

class VariableEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150, required=True)
    tipo_dato = serializers.ChoiceField(choices=TipoDato.choices(), default=TipoDato.TEXTO.value)
    valor_defecto = ValorInicialField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )
    pregunta = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )
    es_inicial = serializers.BooleanField(required=False, default=False)
    descripcion = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class VariableParcialEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150, required=False)
    tipo_dato = serializers.ChoiceField(choices=TipoDato.choices(), required=False)
    valor_defecto = ValorInicialField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )
    pregunta = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )
    es_inicial = serializers.BooleanField(required=False)
    descripcion = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class VariableSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    base_conocimiento_id = serializers.UUIDField(allow_null=True)
    nombre = serializers.CharField()
    tipo_dato = serializers.CharField()
    valor_defecto = serializers.CharField(allow_null=True)
    pregunta = serializers.CharField(allow_null=True)
    es_inicial = serializers.BooleanField()
    descripcion = serializers.CharField(allow_null=True)


# =====================================================================
# REGLA SERIALIZERS
# =====================================================================

class ReglaEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150, required=True)
    descripcion = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    prioridad = serializers.IntegerField(default=0, min_value=0)
    factor_certeza = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal("0.0"),
        max_value=Decimal("1.0"),
    )
    activa = serializers.BooleanField(default=True)


class ReglaParcialEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150, required=False)
    descripcion = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    prioridad = serializers.IntegerField(min_value=0, required=False)
    factor_certeza = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal("0.0"),
        max_value=Decimal("1.0"),
    )
    activa = serializers.BooleanField(required=False)


class ReglaSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    base_conocimiento_id = serializers.UUIDField(allow_null=True)
    nombre = serializers.CharField()
    descripcion = serializers.CharField(allow_null=True)
    prioridad = serializers.IntegerField()
    factor_certeza = serializers.DecimalField(max_digits=4, decimal_places=2, allow_null=True)
    activa = serializers.BooleanField()
    condiciones = CondicionSalidaSerializer(many=True, required=False)
    conclusiones = ConclusionSalidaSerializer(many=True, required=False)


# =====================================================================
# BASE DE CONOCIMIENTO SERIALIZERS
# =====================================================================

class BaseConocimientoSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sistema_experto_id = serializers.UUIDField(allow_null=True)
    nombre = serializers.CharField()
    version = serializers.IntegerField()
    creada_en = serializers.DateTimeField(allow_null=True)
    actualizada_en = serializers.DateTimeField(allow_null=True)
