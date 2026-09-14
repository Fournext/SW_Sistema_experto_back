"""
Modelos ORM Django para el módulo de Inferencia.
Incluye: EjecucionInferencia y DetalleInferencia.
"""
import uuid
from django.db import models
from compartido.constantes.enums import EstadoEjecucion, EstadoReglaInferencia


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
        return f"Inferencia {self.id} [{self.estado}] - {self.fecha_inicio}"


class DetalleInferenciaModel(models.Model):
    """Modelo ORM para registrar la traza y evaluación de cada regla durante la inferencia."""

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
