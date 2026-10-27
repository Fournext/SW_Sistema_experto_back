"""
Modelos ORM Django para el módulo de Inferencia (Sprint 1 + Sprint 2).
Incluye:
- EjecucionInferenciaModel
- DetalleInferenciaModel
- PasoInferenciaModel
- HechoInferidoModel
- ConflictoInferenciaModel
- ConflictoReglaCandidataModel
- ExplicacionConclusionModel
"""
import uuid
from django.conf import settings
from django.db import models
from compartido.constantes.enums import (
    EstadoEjecucion,
    EstadoReglaInferencia,
    ModoInferencia,
    ProcedenciaHecho,
    TipoDato,
)


class EjecucionInferenciaModel(models.Model):
    """Modelo ORM para registrar una ejecución del motor de inferencia."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sistema_experto = models.ForeignKey(
        "sistemas_expertos.SistemaExpertoModel",
        on_delete=models.CASCADE,
        related_name="ejecuciones",
        verbose_name="Sistema Experto",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoEjecucion.choices(),
        default=EstadoEjecucion.INICIADA.value,
        verbose_name="Estado de ejecución",
    )
    modo = models.CharField(
        max_length=20,
        choices=ModoInferencia.choices(),
        default=ModoInferencia.AUTOMATICA.value,
        verbose_name="Modo de ejecución",
    )
    paso_actual = models.IntegerField(default=0, verbose_name="Paso actual")
    asignacion = models.ForeignKey("actividades.AsignacionActividadModel", null=True, blank=True, on_delete=models.SET_NULL, related_name="ejecuciones")
    estudiante = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="ejecuciones_actividades")
    bc_snapshot = models.JSONField(default=dict, blank=True)
    memoria_trabajo_snapshot = models.JSONField(
        default=dict, blank=True, verbose_name="Snapshot memoria de trabajo"
    )
    hechos_iniciales_snapshot = models.JSONField(
        default=list, blank=True, verbose_name="Snapshot hechos iniciales"
    )
    recorrido_por_regla = models.JSONField(default=dict, blank=True)
    es_simulacion = models.BooleanField(
        default=False, verbose_name="¿Es simulación interactiva?"
    )
    fecha_inicio = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de inicio"
    )
    fecha_fin = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha de fin"
    )
    conclusion_final = models.TextField(
        null=True, blank=True, verbose_name="Conclusión final"
    )

    class Meta:
        db_table = "ejecuciones_inferencia"
        verbose_name = "Ejecución de Inferencia"
        verbose_name_plural = "Ejecuciones de Inferencia"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"Inferencia {self.id} [{self.estado}] - Modo: {self.modo} - {self.fecha_inicio}"


class DetalleInferenciaModel(models.Model):
    """Modelo ORM para registrar la traza y evaluación de cada regla durante la inferencia (Sprint 1)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ejecucion = models.ForeignKey(
        EjecucionInferenciaModel,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Ejecución de Inferencia",
    )
    regla = models.ForeignKey(
        "base_conocimiento.ReglaModel",
        on_delete=models.CASCADE,
        related_name="detalles_inferencia",
        verbose_name="Regla evaluada",
    )
    orden = models.IntegerField(verbose_name="Orden en la traza")
    estado_regla = models.CharField(
        max_length=20,
        choices=EstadoReglaInferencia.choices(),
        verbose_name="Estado de la regla",
    )
    condiciones_cumplidas = models.BooleanField(
        null=True, blank=True, verbose_name="¿Condiciones cumplidas?"
    )
    condiciones_evaluadas = models.JSONField(default=list, blank=True)
    paso_numero = models.PositiveIntegerField(null=True, blank=True)
    paso_visual = models.PositiveIntegerField(null=True, blank=True)
    resultado_generado = models.TextField(
        null=True, blank=True, verbose_name="Resultado generado"
    )

    class Meta:
        db_table = "detalles_inferencia"
        verbose_name = "Detalle de Inferencia"
        verbose_name_plural = "Detalles de Inferencia"
        ordering = ["orden"]

    def __str__(self):
        return f"Detalle #{self.orden}: Regla {self.regla_id} -> {self.estado_regla}"


class PasoInferenciaModel(models.Model):
    """Modelo ORM para registrar cada paso discreto en ejecución paso a paso o simulación (Sprint 2 - HU-09)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ejecucion = models.ForeignKey(
        EjecucionInferenciaModel,
        on_delete=models.CASCADE,
        related_name="pasos",
        verbose_name="Ejecución",
    )
    numero_paso = models.IntegerField(verbose_name="Número de paso")
    regla_disparada = models.ForeignKey(
        "base_conocimiento.ReglaModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pasos_disparados",
        verbose_name="Regla disparada",
    )
    memoria_trabajo_pre = models.JSONField(
        default=dict, verbose_name="Memoria de trabajo PRE"
    )
    memoria_trabajo_post = models.JSONField(
        default=dict, verbose_name="Memoria de trabajo POST"
    )
    descripcion = models.TextField(verbose_name="Descripción del paso")
    fecha_ejecucion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de ejecución"
    )

    class Meta:
        db_table = "pasos_inferencia"
        verbose_name = "Paso de Inferencia"
        verbose_name_plural = "Pasos de Inferencia"
        ordering = ["numero_paso"]
        constraints = [
            models.UniqueConstraint(
                fields=["ejecucion", "numero_paso"],
                name="unique_paso_por_ejecucion",
            )
        ]

    def __str__(self):
        return f"Paso #{self.numero_paso} de {self.ejecucion_id}"


class HechoInferidoModel(models.Model):
    """Modelo ORM para registrar hechos generados/derivados durante la inferencia (Sprint 2 - HU-12)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ejecucion = models.ForeignKey(
        EjecucionInferenciaModel,
        on_delete=models.CASCADE,
        related_name="hechos_inferidos",
        verbose_name="Ejecución",
    )
    paso = models.ForeignKey(
        PasoInferenciaModel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hechos_generados",
        verbose_name="Paso en que se generó",
    )
    regla_origen = models.ForeignKey(
        "base_conocimiento.ReglaModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hechos_producidos",
        verbose_name="Regla origen",
    )
    nombre = models.CharField(max_length=150, verbose_name="Nombre del hecho")
    valor = models.CharField(max_length=255, verbose_name="Valor inferido")
    tipo_dato = models.CharField(
        max_length=20,
        choices=TipoDato.choices(),
        default=TipoDato.TEXTO.value,
        verbose_name="Tipo de dato",
    )
    procedencia = models.CharField(
        max_length=50,
        choices=ProcedenciaHecho.choices(),
        default=ProcedenciaHecho.DERIVADO.value,
        verbose_name="Procedencia",
    )
    orden = models.IntegerField(default=1, verbose_name="Orden de deducción")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de deducción")

    class Meta:
        db_table = "hechos_inferidos"
        verbose_name = "Hecho Inferido"
        verbose_name_plural = "Hechos Inferidos"
        ordering = ["orden"]

    def __str__(self):
        return f"{self.nombre} = {self.valor} [{self.procedencia}] (Paso {self.paso_id})"


class ConflictoInferenciaModel(models.Model):
    """Modelo ORM para registrar conjuntos de conflicto durante la inferencia (Sprint 2 - HU-13)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ejecucion = models.ForeignKey(
        EjecucionInferenciaModel,
        on_delete=models.CASCADE,
        related_name="conflictos",
        verbose_name="Ejecución",
    )
    paso = models.ForeignKey(
        PasoInferenciaModel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conflicto_asociado",
        verbose_name="Paso",
    )
    numero_paso = models.IntegerField(verbose_name="Número de paso")
    regla_seleccionada = models.ForeignKey(
        "base_conocimiento.ReglaModel",
        on_delete=models.CASCADE,
        related_name="conflictos_ganados",
        verbose_name="Regla seleccionada (ganadora)",
    )
    criterio_aplicado = models.CharField(
        max_length=100,
        default="PRIORIDAD_DESC_ESPECIFICIDAD_ID",
        verbose_name="Criterio de resolución aplicado",
    )
    explicacion_resolucion = models.TextField(
        verbose_name="Explicación detallada de la resolución"
    )
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        db_table = "conflictos_inferencia"
        verbose_name = "Conflicto de Inferencia"
        verbose_name_plural = "Conflictos de Inferencia"
        ordering = ["numero_paso"]

    def __str__(self):
        return f"Conflicto en Paso #{self.numero_paso}: Ganó {self.regla_seleccionada.nombre}"


class ConflictoReglaCandidataModel(models.Model):
    """Modelo ORM para registrar cada regla candidata evaluada en un conflicto (Sprint 2 - HU-13)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conflicto = models.ForeignKey(
        ConflictoInferenciaModel,
        on_delete=models.CASCADE,
        related_name="reglas_candidatas",
        verbose_name="Conflicto",
    )
    regla = models.ForeignKey(
        "base_conocimiento.ReglaModel",
        on_delete=models.CASCADE,
        related_name="candidaturas_conflicto",
        verbose_name="Regla candidata",
    )
    prioridad = models.IntegerField(verbose_name="Prioridad de la regla")
    fue_seleccionada = models.BooleanField(
        default=False, verbose_name="¿Fue la regla seleccionada?"
    )
    motivo_descarte = models.TextField(
        null=True, blank=True, verbose_name="Motivo del descarte"
    )

    class Meta:
        db_table = "conflictos_reglas_candidatas"
        verbose_name = "Regla Candidata en Conflicto"
        verbose_name_plural = "Reglas Candidatas en Conflicto"
        ordering = ["-prioridad", "regla__nombre"]

    def __str__(self):
        estado = "GANADORA" if self.fue_seleccionada else "DESPRECIADA"
        return f"Candidata {self.regla.nombre} (P: {self.prioridad}) -> {estado}"


class ExplicacionConclusionModel(models.Model):
    """Modelo ORM para la explicabilidad determinista de una conclusión alcanzada (Sprint 2 - HU-17)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ejecucion = models.OneToOneField(
        EjecucionInferenciaModel,
        on_delete=models.CASCADE,
        related_name="explicacion",
        verbose_name="Ejecución explicada",
    )
    conclusion = models.TextField(verbose_name="Conclusión obtenida")
    arbol_justificacion = models.JSONField(
        default=dict,
        verbose_name="Árbol o grafo causal de justificación estructurado",
    )
    texto_explicativo = models.TextField(
        verbose_name="Texto explicativo determinista del razonamiento"
    )
    creada_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de generación")

    class Meta:
        db_table = "explicaciones_conclusion"
        verbose_name = "Explicación de Conclusión"
        verbose_name_plural = "Explicaciones de Conclusión"

    def __str__(self):
        return f"Explicación para Ejecución {self.ejecucion_id} -> {self.conclusion}"
