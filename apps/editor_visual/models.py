"""
Modelos ORM Django para el módulo de Editor Visual.
Incluye: NodoVisual y ConexionVisual.
"""
import uuid
from django.db import models
from django.db.models import F, Q
from compartido.constantes.enums import TipoNodoVisual


class NodoVisualModel(models.Model):
    """Modelo ORM para representar un nodo en el lienzo visual del sistema experto."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sistema_experto = models.ForeignKey(
        "sistemas_expertos.SistemaExpertoModel",
        on_delete=models.CASCADE,
        related_name="nodos_visuales",
        verbose_name="Sistema Experto",
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoNodoVisual.choices(),
        verbose_name="Tipo de nodo",
    )
    referencia_id = models.UUIDField(
        verbose_name="ID de referencia al elemento de dominio"
    )
    posicion_x = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0, verbose_name="Posición X"
    )
    posicion_y = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0, verbose_name="Posición Y"
    )

    class Meta:
        db_table = "nodos_visuales"
        verbose_name = "Nodo Visual"
        verbose_name_plural = "Nodos Visuales"

    def __str__(self):
        return f"Nodo {self.tipo} ({self.id}) en ({self.posicion_x}, {self.posicion_y})"


class ConexionVisualModel(models.Model):
    """Modelo ORM para representar una conexión/arista entre dos nodos visuales."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sistema_experto = models.ForeignKey(
        "sistemas_expertos.SistemaExpertoModel",
        on_delete=models.CASCADE,
        related_name="conexiones_visuales",
        verbose_name="Sistema Experto",
    )
    nodo_origen = models.ForeignKey(
        NodoVisualModel,
        on_delete=models.CASCADE,
        related_name="conexiones_salientes",
        verbose_name="Nodo de origen",
    )
    nodo_destino = models.ForeignKey(
        NodoVisualModel,
        on_delete=models.CASCADE,
        related_name="conexiones_entrantes",
        verbose_name="Nodo de destino",
    )
    etiqueta = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Etiqueta"
    )
    tipo = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Tipo de conexión"
    )

    class Meta:
        db_table = "conexiones_visuales"
        verbose_name = "Conexión Visual"
        verbose_name_plural = "Conexiones Visuales"
        constraints = [
            models.UniqueConstraint(
                fields=["sistema_experto", "nodo_origen", "nodo_destino"],
                name="unique_conexion_origen_destino_sistema",
            ),
            models.CheckConstraint(
                condition=~Q(nodo_origen=F("nodo_destino")),
                name="chk_conexion_no_consigo_mismo",
            ),
        ]

    def __str__(self):
        return f"Conexión: {self.nodo_origen_id} -> {self.nodo_destino_id}"
