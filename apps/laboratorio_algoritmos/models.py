import uuid
from django.conf import settings
from django.db import models


class ProgramaAlgoritmoModel(models.Model):
    """Modelo ORM para almacenar algoritmos escritos por usuarios o docentes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="programas_algoritmo",
        verbose_name="Propietario",
    )
    sistema_experto = models.ForeignKey(
        "sistemas_expertos.SistemaExpertoModel",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="programas_algoritmo",
        verbose_name="Sistema Experto Asociado",
    )
    titulo = models.CharField(max_length=150, verbose_name="Título del Algoritmo")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    codigo_fuente = models.TextField(default="", verbose_name="Código Fuente")
    version_entero = models.IntegerField(default=1, verbose_name="Versión")
    es_publico = models.BooleanField(default=False, verbose_name="¿Es público para alumnos?")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        db_table = "lab_programas_algoritmo"
        verbose_name = "Programa de Algoritmo"
        verbose_name_plural = "Programas de Algoritmos"
        ordering = ["-actualizado_en"]

    def __str__(self):
        return f"{self.titulo} (v{self.version_entero})"


class RevisionProgramaModel(models.Model):
    """Historial inmutable de revisiones de código de un programa."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    programa = models.ForeignKey(
        ProgramaAlgoritmoModel,
        on_delete=models.CASCADE,
        related_name="revisiones",
        verbose_name="Programa",
    )
    numero_revision = models.IntegerField(default=1, verbose_name="Número de revisión")
    codigo_fuente = models.TextField(verbose_name="Código Fuente de la Revisión")
    hash_fuente = models.CharField(max_length=64, blank=True, verbose_name="Hash SHA-256")
    lenguaje_version = models.CharField(max_length=32, default="java-se-1", verbose_name="Versión del Lenguaje")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")

    class Meta:
        db_table = "lab_revisiones_programa"
        verbose_name = "Revisión de Programa"
        verbose_name_plural = "Revisiones de Programas"
        ordering = ["-numero_revision"]

    def __str__(self):
        return f"Rev {self.numero_revision} - {self.programa.titulo}"


class CorridaLaboratorioModel(models.Model):
    """Sesión o corrida de simulación interactiva paso a paso en el laboratorio."""

    ESTADOS = (
        ("INICIADA", "Iniciada"),
        ("EJECUTANDO", "Ejecutando"),
        ("ESPERANDO_ENTRADA", "Esperando Entrada"),
        ("PAUSADA", "Pausada"),
        ("FINALIZADA", "Finalizada"),
        ("ERROR", "Error"),
        ("CANCELADA", "Cancelada"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="corridas_laboratorio",
        verbose_name="Usuario",
    )
    programa = models.ForeignKey(
        ProgramaAlgoritmoModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corridas",
        verbose_name="Programa",
    )
    sistema_experto = models.ForeignKey(
        "sistemas_expertos.SistemaExpertoModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corridas_laboratorio",
        verbose_name="Sistema Experto",
    )
    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default="INICIADA",
        verbose_name="Estado de Corrida",
    )
    codigo_fuente = models.TextField(default="", blank=True, verbose_name="Código Fuente de la Corrida")
    estado_vm_json = models.JSONField(default=dict, blank=True, verbose_name="Estado VM serializado")
    snapshot_bc_json = models.JSONField(default=dict, blank=True, verbose_name="Snapshot de BC")
    total_pasos = models.IntegerField(default=0, verbose_name="Total de pasos ejecutados")
    mensaje_salida = models.TextField(blank=True, default="", verbose_name="Mensaje de salida o error")
    creada_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    actualizada_en = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        db_table = "lab_corridas_laboratorio"
        verbose_name = "Corrida de Laboratorio"
        verbose_name_plural = "Corridas de Laboratorio"
        ordering = ["-creada_en"]

    def __str__(self):
        return f"Corrida {self.id} ({self.estado})"


class PasoEjecucionModel(models.Model):
    """Paso individual o traza visual registrada durante una corrida."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corrida = models.ForeignKey(
        CorridaLaboratorioModel,
        on_delete=models.CASCADE,
        related_name="pasos",
        verbose_name="Corrida",
    )
    numero_paso = models.IntegerField(verbose_name="Número de Paso")
    pc = models.IntegerField(default=0, verbose_name="Contador de Programa (PC)")
    linea = models.IntegerField(default=1, verbose_name="Línea en código fuente")
    columna = models.IntegerField(default=1, verbose_name="Columna en código fuente")
    evento_json = models.JSONField(default=dict, blank=True, verbose_name="Detalle del Evento")
    delta_json = models.JSONField(default=dict, blank=True, verbose_name="Delta de Memoria/Entorno")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")

    class Meta:
        db_table = "lab_pasos_ejecucion"
        verbose_name = "Paso de Ejecución"
        verbose_name_plural = "Pasos de Ejecución"
        ordering = ["numero_paso"]

    def __str__(self):
        return f"Paso {self.numero_paso} (Línea {self.linea}:{self.columna}) - Corrida {self.corrida_id}"
