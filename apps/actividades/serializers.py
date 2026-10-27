"""
Serializadores REST para el módulo de Actividades Educativas (Sprint 2 - HU-23, HU-24, HU-25).
"""
from rest_framework import serializers

from compartido.constantes.enums import (
    DificultadActividad,
    EstadoActividad,
    EstadoAsignacion,
    EstadoEntrega,
)


class CursoSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField(allow_null=True, required=False)
    docente_id = serializers.IntegerField(read_only=True)
    activo = serializers.BooleanField(read_only=True)
    creado_en = serializers.DateTimeField(read_only=True)


class CrearCursoSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=50)
    nombre = serializers.CharField(max_length=150)
    descripcion = serializers.CharField(allow_blank=True, required=False, default="")


class ActividadEducativaSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    docente_id = serializers.IntegerField(read_only=True)
    docente_username = serializers.CharField(allow_null=True, read_only=True)
    sistema_experto_id = serializers.UUIDField()
    sistema_experto_nombre = serializers.CharField(allow_null=True, read_only=True)
    titulo = serializers.CharField()
    instrucciones = serializers.CharField()
    dificultad = serializers.CharField()
    estado = serializers.CharField()
    activa = serializers.BooleanField(read_only=True)
    creada_en = serializers.DateTimeField(read_only=True)
    actualizada_en = serializers.DateTimeField(read_only=True)


class CrearActividadEducativaSerializer(serializers.Serializer):
    sistema_experto_id = serializers.UUIDField()
    titulo = serializers.CharField(max_length=200)
    instrucciones = serializers.CharField()
    dificultad = serializers.ChoiceField(
        choices=DificultadActividad.choices(), default=DificultadActividad.MEDIA.value
    )
    estado = serializers.ChoiceField(
        choices=EstadoActividad.choices(), default=EstadoActividad.BORRADOR.value
    )


class ActualizarActividadEducativaSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=200, required=False)
    instrucciones = serializers.CharField(required=False)
    dificultad = serializers.ChoiceField(choices=DificultadActividad.choices(), required=False)
    estado = serializers.ChoiceField(choices=EstadoActividad.choices(), required=False)


class AsignacionActividadSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    actividad_id = serializers.UUIDField()
    actividad_titulo = serializers.CharField(allow_null=True, read_only=True)
    curso_id = serializers.UUIDField()
    curso_codigo = serializers.CharField(allow_null=True, read_only=True)
    curso_nombre = serializers.CharField(allow_null=True, read_only=True)
    fecha_asignacion = serializers.DateTimeField(read_only=True)
    fecha_limite = serializers.DateTimeField(allow_null=True, required=False)
    estado = serializers.CharField(read_only=True)


class CrearAsignacionActividadSerializer(serializers.Serializer):
    actividad_id = serializers.UUIDField()
    curso_id = serializers.UUIDField()
    fecha_limite = serializers.DateTimeField(required=False, allow_null=True, default=None)


class EntregaActividadSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    asignacion_id = serializers.UUIDField()
    estudiante_id = serializers.IntegerField(read_only=True)
    estudiante_username = serializers.CharField(allow_null=True, read_only=True)
    estado = serializers.CharField()
    solucion_texto = serializers.CharField(allow_null=True, required=False)
    hechos_ingresados = serializers.ListField(child=serializers.DictField(), default=list)
    ejecucion_inferencia_id = serializers.UUIDField(allow_null=True, required=False)
    fecha_envio = serializers.DateTimeField(allow_null=True, read_only=True)
    creada_en = serializers.DateTimeField(read_only=True)
    actualizada_en = serializers.DateTimeField(read_only=True)


class GuardarBorradorEntregaSerializer(serializers.Serializer):
    solucion_texto = serializers.CharField(required=False, allow_blank=True, default="")
    hechos_ingresados = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )
    ejecucion_inferencia_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class EnviarEntregaSerializer(serializers.Serializer):
    solucion_texto = serializers.CharField(required=False, allow_blank=True, default="")
    hechos_ingresados = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )
    ejecucion_inferencia_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class ActividadEstudianteResumenSerializer(serializers.Serializer):
    asignacion_id = serializers.UUIDField()
    actividad_id = serializers.UUIDField()
    actividad_titulo = serializers.CharField()
    curso_id = serializers.UUIDField()
    curso_codigo = serializers.CharField()
    curso_nombre = serializers.CharField()
    fecha_asignacion = serializers.DateTimeField()
    fecha_limite = serializers.DateTimeField(allow_null=True)
    estado_asignacion = serializers.CharField()
    tiene_entrega = serializers.BooleanField()
    estado_entrega = serializers.CharField()
    entrega_id = serializers.UUIDField(allow_null=True)
