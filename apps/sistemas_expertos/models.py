"""
Modelos ORM Django para el módulo de Sistemas Expertos.
"""
import uuid
from django.db import models
from compartido.constantes.enums import EstadoSistema


class SistemaExpertoModel(models.Model):
    """Modelo ORM para la persistencia de un Sistema Experto."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=150, verbose_name="Nombre del sistema")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    estado = models.CharField(
        max_length=20,
        choices=EstadoSistema.choices(),
        default=EstadoSistema.BORRADOR.value,
        verbose_name="Estado",
    )
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        db_table = "sistemas_expertos"
        verbose_name = "Sistema Experto"
        verbose_name_plural = "Sistemas Expertos"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.nombre} ({self.estado})"
