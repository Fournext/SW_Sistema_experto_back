"""
Serializadores REST para el Laboratorio de Algoritmos de Inferencia.
"""
from rest_framework import serializers
from apps.laboratorio_algoritmos.models import (
    ComparticionProgramaModel,
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
    snapshot_bc = serializers.DictField(required=False, default=dict)


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
    snapshot_bc = serializers.SerializerMethodField()

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
            "snapshot_bc",
            "creada_en",
            "actualizada_en",
        ]

    def get_estado_vm(self, obj):
        return obj.estado_vm_json

    def get_snapshot_bc(self, obj):
        return obj.snapshot_bc_json


class ProgramaAlgoritmoSerializer(serializers.ModelSerializer):
    owner_nombre = serializers.SerializerMethodField()
    programa_origen_titulo = serializers.SerializerMethodField()
    es_propio = serializers.SerializerMethodField()
    modo_acceso = serializers.SerializerMethodField()

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
            "programa_origen",
            "programa_origen_titulo",
            "es_propio",
            "modo_acceso",
            "es_publico",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = [
            "id",
            "owner",
            "owner_nombre",
            "programa_origen_titulo",
            "es_propio",
            "modo_acceso",
            "creado_en",
            "actualizado_en",
        ]

    def get_owner_nombre(self, obj):
        return obj.owner.get_full_name() or obj.owner.username

    def get_programa_origen_titulo(self, obj):
        return obj.programa_origen.titulo if obj.programa_origen else None

    def get_es_propio(self, obj):
        req = self.context.get("request")
        if req and req.user and req.user.is_authenticated:
            return obj.owner_id == req.user.id
        return True

    def get_modo_acceso(self, obj):
        return self.context.get("modo_acceso", "EDICION" if self.get_es_propio(obj) else "LECTURA")


class ComparticionProgramaSerializer(serializers.ModelSerializer):
    curso_codigo = serializers.CharField(source="curso.codigo", read_only=True)
    curso_nombre = serializers.CharField(source="curso.nombre", read_only=True)
    docente_nombre = serializers.SerializerMethodField()
    programa_titulo = serializers.CharField(source="programa.titulo", read_only=True)
    programa_descripcion = serializers.CharField(source="programa.descripcion", read_only=True)
    codigo_fuente = serializers.CharField(source="programa.codigo_fuente", read_only=True)
    sistema_experto_id = serializers.UUIDField(source="programa.sistema_experto_id", read_only=True)

    class Meta:
        model = ComparticionProgramaModel
        fields = [
            "id",
            "programa",
            "programa_titulo",
            "programa_descripcion",
            "codigo_fuente",
            "sistema_experto_id",
            "curso",
            "curso_codigo",
            "curso_nombre",
            "docente",
            "docente_nombre",
            "modo_acceso",
            "activa",
            "fecha_compartido",
        ]
        read_only_fields = ["id", "docente", "fecha_compartido"]

    def get_docente_nombre(self, obj):
        return obj.docente.get_full_name() or obj.docente.username


class CompartirProgramaEntradaSerializer(serializers.Serializer):
    curso_id = serializers.UUIDField()
    modo_acceso = serializers.ChoiceField(choices=["LECTURA", "COPIA_EDICION"], default="LECTURA")


class ForkProgramaEntradaSerializer(serializers.Serializer):
    titulo = serializers.CharField(required=False, allow_blank=True)


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

