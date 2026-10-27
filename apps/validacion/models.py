"""
Modelos ORM Django para el módulo de Validación de Bases de Conocimiento (Sprint 2 - HU-18, HU-19).
Incluye:
- ValidacionBaseModel
- IncidenciaValidacionModel
"""
import uuid
from django.db import models
from compartido.constantes.enums import SeveridadIncidencia, TipoIncidencia


class ValidacionBaseModel(models.Model):
    """Registro de una corrida de validación sobre una Base de Conocimiento."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_conocimiento = models.ForeignKey(
        "base_conocimiento.BaseConocimientoModel",
        on_delete=models.CASCADE,
        related_name="validaciones",
        verbose_name="Base de Conocimiento",
    )
    fecha_validacion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de validación"
    )
    es_valida = models.BooleanField(
        default=True, verbose_name="¿Es base válida (sin errores)?"
    )
    total_errores = models.IntegerField(default=0, verbose_name="Total de errores")
    total_advertencias = models.IntegerField(
        default=0, verbose_name="Total de advertencias"
    )
    resumen = models.TextField(
        null=True, blank=True, verbose_name="Resumen de validación"
    )

    class Meta:
        db_table = "validaciones_base"
        verbose_name = "Validación de Base de Conocimiento"
        verbose_name_plural = "Validaciones de Bases de Conocimiento"
        ordering = ["-fecha_validacion"]

    def __str__(self):
        estado = "VÁLIDA" if self.es_valida else "CON ERRORES"
        return f"Validación {self.id} [{estado}] - {self.total_errores} errores, {self.total_advertencias} advertencias"


class IncidenciaValidacionModel(models.Model):
    """Incidencia o defecto detectado en una regla, condición, conclusión, hecho o variable."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    validacion = models.ForeignKey(
        ValidacionBaseModel,
        on_delete=models.CASCADE,
        related_name="incidencias",
        verbose_name="Validación",
    )
    codigo = models.CharField(max_length=50, verbose_name="Código de incidencia")
    tipo = models.CharField(
        max_length=50,
        choices=TipoIncidencia.choices(),
        verbose_name="Tipo de incidencia",
    )
    severidad = models.CharField(
        max_length=20,
        choices=SeveridadIncidencia.choices(),
        verbose_name="Severidad",
    )
    entidad_tipo = models.CharField(
        max_length=50, verbose_name="Tipo de entidad afectada"
    )
    entidad_id = models.UUIDField(
        null=True, blank=True, verbose_name="ID de la entidad afectada"
    )
    entidad_nombre = models.CharField(
        max_length=150, null=True, blank=True, verbose_name="Nombre de la entidad"
    )
    descripcion = models.TextField(verbose_name="Descripción del problema")
    posible_causa = models.TextField(verbose_name="Posible causa")
    sugerencia = models.TextField(verbose_name="Sugerencia de corrección")
    creada_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de detección")

    class Meta:
        db_table = "incidencias_validacion"
        verbose_name = "Incidencia de Validación"
        verbose_name_plural = "Incidencias de Validación"
        ordering = ["severidad", "codigo"]

    def __str__(self):
        return f"[{self.severidad}] {self.codigo} en {self.entidad_tipo} '{self.entidad_nombre}': {self.descripcion}"
