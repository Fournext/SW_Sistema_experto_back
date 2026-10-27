"""
Modelos ORM Django para el módulo de Actividades Educativas (Sprint 2 - HU-23, HU-24, HU-25).
Incluye:
- CursoModel (entidad mínima requerida para soportar asignaciones del Sprint 2)
- ActividadEducativaModel
- AsignacionActividadModel
- EntregaActividadModel
"""
import uuid
from django.conf import settings
from django.db import models
from .models_cursos import generar_codigo_ingreso, generar_token_ingreso
from compartido.constantes.enums import (
    DificultadActividad,
    EstadoActividad,
    EstadoAsignacion,
    EstadoEntrega,
)


class CursoModel(models.Model):
    """Modelo ORM mínimo para un Curso académico (requerido para HU-24 y HU-25)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código del curso")
    codigo_ingreso = models.CharField(max_length=20, unique=True, default=generar_codigo_ingreso, editable=False)
    token_ingreso = models.CharField(max_length=128, unique=True, default=generar_token_ingreso, editable=False)
    nombre = models.CharField(max_length=150, verbose_name="Nombre de la asignatura")
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción")
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cursos_docente",
        verbose_name="Docente titular",
    )
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        db_table = "cursos"
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ActividadEducativaModel(models.Model):
    """Modelo ORM para una Actividad Educativa creada por un docente (HU-23)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="actividades_creadas",
        verbose_name="Docente responsable",
    )
    sistema_experto = models.ForeignKey(
        "sistemas_expertos.SistemaExpertoModel",
        on_delete=models.CASCADE,
        related_name="actividades",
        verbose_name="Sistema Experto asociado",
        null=True, blank=True,
    )
    titulo = models.CharField(max_length=200, verbose_name="Título de la actividad")
    tipo = models.CharField(max_length=20, choices=[("ANALISIS_BC", "Análisis de BC"), ("CREACION_BC", "Creación de BC")], default="ANALISIS_BC")
    permisos = models.JSONField(default=dict, blank=True)
    instrucciones = models.TextField(verbose_name="Instrucciones didácticas")
    dificultad = models.CharField(
        max_length=20,
        choices=DificultadActividad.choices(),
        default=DificultadActividad.MEDIA.value,
        verbose_name="Dificultad",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoActividad.choices(),
        default=EstadoActividad.BORRADOR.value,
        verbose_name="Estado de publicación",
    )
    activa = models.BooleanField(default=True, verbose_name="¿Activa?")
    creada_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    actualizada_en = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        db_table = "actividades_educativas"
        verbose_name = "Actividad Educativa"
        verbose_name_plural = "Actividades Educativas"
        ordering = ["-creada_en"]

    def __str__(self):
        return f"Actividad: {self.titulo} [{self.dificultad}]"


class AsignacionActividadModel(models.Model):
    """Modelo ORM para la asignación de una actividad educativa a un curso (HU-24)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actividad = models.ForeignKey(
        ActividadEducativaModel,
        on_delete=models.CASCADE,
        related_name="asignaciones",
        verbose_name="Actividad",
    )
    curso = models.ForeignKey(
        CursoModel,
        on_delete=models.CASCADE,
        related_name="asignaciones",
        verbose_name="Curso",
    )
    fecha_asignacion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de asignación"
    )
    fecha_limite = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha límite de entrega"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoAsignacion.choices(),
        default=EstadoAsignacion.VIGENTE.value,
        verbose_name="Estado de asignación",
    )

    class Meta:
        db_table = "asignaciones_actividades"
        verbose_name = "Asignación de Actividad"
        verbose_name_plural = "Asignaciones de Actividades"
        ordering = ["-fecha_asignacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["actividad", "curso"],
                name="unique_actividad_por_curso",
            )
        ]

    def __str__(self):
        return f"Asignación: {self.actividad.titulo} en curso {self.curso.codigo}"


class EntregaActividadModel(models.Model):
    """Modelo ORM para la entrega o borrador de solución de un estudiante (HU-25)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asignacion = models.ForeignKey(
        AsignacionActividadModel,
        on_delete=models.CASCADE,
        related_name="entregas",
        verbose_name="Asignación",
    )
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="entregas_actividades",
        verbose_name="Estudiante",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoEntrega.choices(),
        default=EstadoEntrega.BORRADOR.value,
        verbose_name="Estado de la entrega",
    )
    numero_revision = models.PositiveIntegerField(default=0)
    ejecuciones_ids = models.JSONField(default=list, blank=True)
    solucion_texto = models.TextField(
        null=True, blank=True, verbose_name="Texto o justificación de la solución"
    )
    hechos_ingresados = models.JSONField(
        default=list, blank=True, verbose_name="Hechos iniciales configurados"
    )
    ejecucion_inferencia = models.ForeignKey(
        "inferencia.EjecucionInferenciaModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="entregas_asociadas",
        verbose_name="Ejecución de inferencia de la simulación",
    )
    fecha_envio = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha de envío definitivo"
    )
    creada_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    actualizada_en = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        db_table = "entregas_actividades"
        verbose_name = "Entrega de Actividad"
        verbose_name_plural = "Entregas de Actividades"
        ordering = ["-actualizada_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["asignacion", "estudiante"],
                name="unique_entrega_estudiante_por_asignacion",
            )
        ]

    def __str__(self):
        return f"Entrega de {self.estudiante.username} para {self.asignacion.actividad.titulo} [{self.estado}]"


class TrabajoActividadModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asignacion = models.ForeignKey(AsignacionActividadModel, on_delete=models.CASCADE, related_name="trabajos")
    estudiante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trabajos_actividades")
    sistema_experto = models.OneToOneField("sistemas_expertos.SistemaExpertoModel", on_delete=models.CASCADE, related_name="trabajo_actividad")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["asignacion", "estudiante"], name="unique_trabajo_asignacion_estudiante")]


class RevisionEntregaModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entrega = models.ForeignKey(EntregaActividadModel, on_delete=models.CASCADE, related_name="revisiones")
    numero = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["numero"]
        constraints = [models.UniqueConstraint(fields=["entrega", "numero"], name="unique_revision_entrega_numero")]


class ComentarioEntregaModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(RevisionEntregaModel, on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    texto = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en"]


from .models_cursos import MatriculaCursoModel  # noqa: E402,F401
