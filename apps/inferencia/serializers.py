"""
Serializadores DRF para el módulo de Inferencia y Simulación (Sprint 1 + Sprint 2).
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
    condiciones_evaluadas = serializers.JSONField(default=list)
    paso_numero = serializers.IntegerField(allow_null=True, default=None)
    paso_visual = serializers.IntegerField(allow_null=True, default=None)
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


class IniciarSimulacionEntradaSerializer(serializers.Serializer):
    hechos_iniciales = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="Lista opcional de hechos personalizados para la simulación [{'nombre': '...', 'valor': '...'}]",
    )


class HechoInferidoSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    ejecucion_id = serializers.UUIDField()
    paso_id = serializers.UUIDField(allow_null=True)
    regla_origen_id = serializers.UUIDField(allow_null=True)
    regla_origen_nombre = serializers.CharField(allow_null=True)
    nombre = serializers.CharField()
    valor = serializers.CharField()
    tipo_dato = serializers.CharField()
    procedencia = serializers.CharField()
    orden = serializers.IntegerField()
    creado_en = serializers.DateTimeField(allow_null=True)


class ConflictoCandidataSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    regla_id = serializers.UUIDField()
    regla_nombre = serializers.CharField()
    prioridad = serializers.IntegerField()
    fue_seleccionada = serializers.BooleanField()
    motivo_descarte = serializers.CharField(allow_null=True)


class ConflictoInferenciaSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    ejecucion_id = serializers.UUIDField()
    paso_id = serializers.UUIDField(allow_null=True)
    numero_paso = serializers.IntegerField()
    regla_seleccionada_id = serializers.UUIDField()
    regla_seleccionada_nombre = serializers.CharField()
    criterio_aplicado = serializers.CharField()
    explicacion_resolucion = serializers.CharField()
    reglas_candidatas = ConflictoCandidataSalidaSerializer(many=True)
    creado_en = serializers.DateTimeField(allow_null=True)


class PasoInferenciaSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    ejecucion_id = serializers.UUIDField()
    numero_paso = serializers.IntegerField()
    regla_disparada_id = serializers.UUIDField(allow_null=True)
    regla_nombre = serializers.CharField(allow_null=True)
    memoria_trabajo_pre = serializers.JSONField()
    memoria_trabajo_post = serializers.JSONField()
    descripcion = serializers.CharField()
    fecha_ejecucion = serializers.DateTimeField(allow_null=True)


class ReglaDisparadaExplicacionSerializer(serializers.Serializer):
    id = serializers.CharField()
    nombre = serializers.CharField()
    prioridad = serializers.IntegerField(allow_null=True)
    factor_certeza = serializers.FloatField(allow_null=True)
    condiciones_cumplidas = serializers.ListField(child=serializers.CharField())
    consecuencia = serializers.CharField(allow_blank=True)


class ExplicacionConclusionSalidaSerializer(serializers.Serializer):
    conclusion = serializers.CharField(allow_null=True)
    texto = serializers.CharField()
    arbol = serializers.JSONField()
    reglas_involucradas = serializers.ListField(child=serializers.CharField(), required=False)
    hechos_clave = serializers.ListField(child=serializers.CharField(), required=False)
    conclusion_nombre = serializers.CharField(allow_null=True)
    conclusion_valor = serializers.JSONField(allow_null=True)
    factor_certeza_final = serializers.FloatField(allow_null=True)
    hechos_iniciales_relevantes = serializers.ListField(child=serializers.DictField())
    hechos_intermedios_derivados = serializers.ListField(child=serializers.DictField())
    reglas_disparadas = ReglaDisparadaExplicacionSerializer(many=True)
    cadena_razonamiento = serializers.ListField(child=serializers.CharField())
    resumen_explicativo = serializers.CharField()


class EjecucionInferenciaSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sistema_experto_id = serializers.UUIDField(allow_null=True)
    estado = serializers.SerializerMethodField()
    modo = serializers.SerializerMethodField()
    paso_actual = serializers.IntegerField()
    memoria_trabajo_snapshot = serializers.JSONField()
    hechos_iniciales_snapshot = serializers.JSONField()
    es_simulacion = serializers.BooleanField()
    fecha_inicio = serializers.DateTimeField(allow_null=True)
    fecha_fin = serializers.DateTimeField(allow_null=True)
    conclusion_final = serializers.CharField(allow_null=True)
    numero_vuelta = serializers.SerializerMethodField()
    siguiente_regla = serializers.SerializerMethodField()
    paso_visual_actual = serializers.SerializerMethodField()

    def get_paso_visual_actual(self, obj):
        return (getattr(obj, "recorrido_por_regla", None) or {}).get("paso_visual_actual", obj.paso_actual)

    def get_numero_vuelta(self, obj):
        return (getattr(obj, "recorrido_por_regla", None) or {}).get("numero_vuelta", 1)

    def get_siguiente_regla(self, obj):
        if self.context.get("es_historial"):
            return None
        from apps.inferencia.recorrido import pendientes_recorrido
        from apps.base_conocimiento.models import ReglaModel
        from apps.inferencia.models import PasoInferenciaModel

        estado = getattr(obj.estado, "value", obj.estado)
        if estado in ("FINALIZADA", "COMPLETADA", "ERROR") or not obj.es_simulacion:
            return None
        reglas = ReglaModel.objects.filter(
            base_conocimiento__sistema_experto_id=obj.sistema_experto_id, activa=True,
        )
        ejecutadas = PasoInferenciaModel.objects.filter(
            ejecucion_id=obj.id, regla_disparada_id__isnull=False,
        ).values_list("regla_disparada_id", flat=True)
        pendientes = pendientes_recorrido(reglas, ejecutadas, obj.recorrido_por_regla or {})
        if not pendientes:
            return None
        regla = pendientes[0]
        return {"id": str(regla.id), "nombre": regla.nombre, "prioridad": regla.prioridad}

    def get_estado(self, obj) -> str:
        val = getattr(obj, "estado", "")
        return val.value if hasattr(val, "value") else str(val)

    def get_modo(self, obj) -> str:
        val = getattr(obj, "modo", "")
        return val.value if hasattr(val, "value") else str(val)


class HistorialInferenciaSalidaSerializer(EjecucionInferenciaSalidaSerializer):
    total_pasos = serializers.IntegerField()
    total_reglas_evaluadas = serializers.IntegerField()
    total_reglas_disparadas = serializers.IntegerField()


class DetalleInferenciaSalidaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    ejecucion_id = serializers.UUIDField(allow_null=True)
    regla_id = serializers.UUIDField(allow_null=True)
    nombre_regla = serializers.SerializerMethodField()
    regla_nombre = serializers.SerializerMethodField()
    regla = serializers.SerializerMethodField()
    orden = serializers.IntegerField()
    orden_evaluacion = serializers.IntegerField(source="orden")
    estado = serializers.SerializerMethodField()
    estado_regla = serializers.SerializerMethodField()
    condiciones_cumplidas = serializers.SerializerMethodField()
    condiciones_evaluadas = serializers.JSONField(default=list)
    paso_numero = serializers.IntegerField(allow_null=True, default=None)
    paso_visual = serializers.IntegerField(allow_null=True, default=None)
    resultado_generado = serializers.CharField(allow_null=True)

    def get_estado(self, obj) -> str:
        val = getattr(obj, "estado_regla", None) or getattr(obj, "estado", "")
        return val.value if hasattr(val, "value") else str(val)

    def get_estado_regla(self, obj) -> str:
        return self.get_estado(obj)

    def get_nombre_regla(self, obj) -> str:
        if hasattr(obj, "regla_nombre") and obj.regla_nombre:
            return obj.regla_nombre
        if hasattr(obj, "nombre_regla") and obj.nombre_regla:
            return obj.nombre_regla
        regla_id = getattr(obj, "regla_id", None)
        if regla_id:
            from apps.base_conocimiento.models import ReglaModel
            r = ReglaModel.objects.filter(id=regla_id).only("nombre").first()
            if r:
                return r.nombre
        return "Regla"

    def get_regla_nombre(self, obj) -> str:
        return self.get_nombre_regla(obj)

    def get_regla(self, obj) -> str:
        return self.get_nombre_regla(obj)

    def get_condiciones_cumplidas(self, obj):
        val = getattr(obj, "condiciones_cumplidas", None)
        if isinstance(val, bool):
            return [val]
        if isinstance(val, (list, tuple)):
            return list(val)
        return []
