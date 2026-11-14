"""
Serializadores REST para el Laboratorio de Algoritmos de Inferencia.
"""
from rest_framework import serializers
from apps.laboratorio_algoritmos.models import (
    CorridaLaboratorioModel,
    PasoEjecucionModel,
    ProgramaAlgoritmoModel,
    RevisionProgramaModel,
)


class CompilarCodigoEntradaSerializer(serializers.Serializer):
    codigo_fuente = serializers.CharField(allow_blank=True)


class ErrorCompilacionSerializer(serializers.Serializer):
    mensaje = serializers.CharField()
    linea = serializers.IntegerField(required=False, allow_null=True)
    columna = serializers.IntegerField(required=False, allow_null=True)
    offset = serializers.IntegerField(required=False, allow_null=True)
    fase = serializers.CharField(default="sintaxis")


class CompilarCodigoSalidaSerializer(serializers.Serializer):
    valido = serializers.BooleanField()
    errores = ErrorCompilacionSerializer(many=True)
    warnings = serializers.ListField(child=serializers.DictField(), default=list)
    ast = serializers.DictField(required=False, allow_null=True)


class IniciarEjecucionEntradaSerializer(serializers.Serializer):
    sistema_experto_id = serializers.UUIDField(required=False, allow_null=True)
    programa_id = serializers.UUIDField(required=False, allow_null=True)
    codigo_fuente = serializers.CharField(required=False, allow_blank=True)
    orden_reglas_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    hechos_iniciales_override = serializers.DictField(required=False, default=dict)
    parametros_iniciales = serializers.DictField(required=False, default=dict)


class AvanzarEjecucionEntradaSerializer(serializers.Serializer):
    modo = serializers.ChoiceField(choices=["LINE_STEP", "INSTRUCTION_STEP", "RUN_TO_END"], default="LINE_STEP")
    max_pasos = serializers.IntegerField(default=100, min_value=1, max_value=5000)


class ResponderPreguntaEntradaSerializer(serializers.Serializer):
    valor = serializers.CharField(allow_blank=True, default="")
    cancelada = serializers.BooleanField(default=False)


class EstadoVMSalidaSerializer(serializers.Serializer):
    pc = serializers.IntegerField()
    estado = serializers.CharField()
    linea_actual = serializers.IntegerField(allow_null=True)
    columna_actual = serializers.IntegerField(allow_null=True)
    variables_locales = serializers.DictField()
    base_hechos = serializers.ListField(child=serializers.DictField())
    reglas = serializers.ListField(child=serializers.DictField())
    pila_hn = serializers.ListField(child=serializers.DictField(), required=False)
    cola_q = serializers.ListField(child=serializers.DictField(), required=False)
    pregunta_pendiente = serializers.DictField(required=False, allow_null=True)
    ultimo_evento = serializers.DictField(required=False, allow_null=True)
    salida_consola = serializers.ListField(child=serializers.CharField(), default=list)


class CorridaLaboratorioSalidaSerializer(serializers.ModelSerializer):
    estado_vm = serializers.SerializerMethodField()

    class Meta:
        model = CorridaLaboratorioModel
        fields = [
            "id",
            "programa",
            "sistema_experto",
            "estado",
            "total_pasos",
            "mensaje_salida",
            "estado_vm",
            "creada_en",
            "actualizada_en",
        ]

    def get_estado_vm(self, obj):
        return obj.estado_vm_json


class ProgramaAlgoritmoSerializer(serializers.ModelSerializer):
    owner_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ProgramaAlgoritmoModel
        fields = [
            "id",
            "owner",
            "owner_nombre",
            "sistema_experto",
            "titulo",
            "descripcion",
            "codigo_fuente",
            "version_entero",
            "es_publico",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "owner", "owner_nombre", "creado_en", "actualizado_en"]

    def get_owner_nombre(self, obj):
        return obj.owner.get_full_name() or obj.owner.username


class RevisionProgramaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevisionProgramaModel
        fields = [
            "id",
            "programa",
            "numero_revision",
            "codigo_fuente",
            "hash_fuente",
            "lenguaje_version",
            "creado_en",
        ]
        read_only_fields = ["id", "creado_en"]

