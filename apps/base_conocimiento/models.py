"""
Modelos ORM Django para el módulo de Base de Conocimiento.
Incluye: BaseConocimiento, Hecho, Variable, Regla, Condicion, Conclusion.
"""
import uuid
from django.db import models
from django.db.models import Q
from compartido.constantes.enums import TipoDato, OperadorCondicion


class BaseConocimientoModel(models.Model):
    """Modelo ORM para la Base de Conocimiento asociada 1:1 a un Sistema Experto."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sistema_experto = models.OneToOneField(
        "sistemas_expertos.SistemaExpertoModel",
        on_delete=models.CASCADE,
        related_name="base_conocimiento",
        verbose_name="Sistema Experto",
    )
    nombre = models.CharField(max_length=150, verbose_name="Nombre")
    version = models.IntegerField(default=1, verbose_name="Versión")
    creada_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    actualizada_en = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")

    class Meta:
        db_table = "bases_conocimiento"
        verbose_name = "Base de Conocimiento"
        verbose_name_plural = "Bases de Conocimiento"
        ordering = ["-creada_en"]

    def __str__(self):
        return f"{self.nombre} (v{self.version})"


class HechoModel(models.Model):
    """Modelo ORM para un Hecho en la base de conocimiento."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_conocimiento = models.ForeignKey(
        BaseConocimientoModel,
        on_delete=models.CASCADE,
        related_name="hechos",
        verbose_name="Base de Conocimiento",
    )
    nombre = models.CharField(max_length=150, verbose_name="Nombre del hecho")
    valor = models.CharField(max_length=255, null=True, blank=True, verbose_name="Valor")
    tipo_dato = models.CharField(
        max_length=20,
        choices=TipoDato.choices(),
        default=TipoDato.TEXTO.value,
        verbose_name="Tipo de dato",
    )
    opciones = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Opciones disponibles",
    )
    pregunta = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Pregunta para el usuario",
    )
    es_inicial = models.BooleanField(default=True, verbose_name="¿Es hecho inicial?")

    class Meta:
        db_table = "hechos"
        verbose_name = "Hecho"
        verbose_name_plural = "Hechos"
        constraints = [
            models.UniqueConstraint(
                fields=["base_conocimiento", "nombre"],
                name="unique_hecho_nombre_por_base",
            )
        ]
        ordering = ["nombre"]

    def __str__(self):
        return f"Hecho: {self.nombre} = {self.valor} ({self.tipo_dato})"


class VariableModel(models.Model):
    """Modelo ORM para una Variable en la base de conocimiento."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_conocimiento = models.ForeignKey(
        BaseConocimientoModel,
        on_delete=models.CASCADE,
        related_name="variables",
        verbose_name="Base de Conocimiento",
    )
    nombre = models.CharField(max_length=150, verbose_name="Nombre de la variable")
    tipo_dato = models.CharField(
        max_length=20,
        choices=TipoDato.choices(),
        default=TipoDato.TEXTO.value,
        verbose_name="Tipo de dato",
    )
    valor_defecto = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Valor por defecto"
    )
    pregunta = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Pregunta para el usuario",
    )
    es_inicial = models.BooleanField(default=False, verbose_name="¿Es variable inicial?")
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción")

    class Meta:
        db_table = "variables"
        verbose_name = "Variable"
        verbose_name_plural = "Variables"
        constraints = [
            models.UniqueConstraint(
                fields=["base_conocimiento", "nombre"],
                name="unique_variable_nombre_por_base",
            )
        ]
        ordering = ["nombre"]

    def __str__(self):
        return f"Variable: {self.nombre} ({self.tipo_dato})"


class ReglaModel(models.Model):
    """Modelo ORM para una Regla en la base de conocimiento."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_conocimiento = models.ForeignKey(
        BaseConocimientoModel,
        on_delete=models.CASCADE,
        related_name="reglas",
        verbose_name="Base de Conocimiento",
    )
    nombre = models.CharField(max_length=150, verbose_name="Nombre de la regla")
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción")
    prioridad = models.IntegerField(default=0, verbose_name="Prioridad")
    factor_certeza = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Factor de certeza",
    )
    activa = models.BooleanField(default=True, verbose_name="¿Activa?")

    class Meta:
        db_table = "reglas"
        verbose_name = "Regla"
        verbose_name_plural = "Reglas"
        constraints = [
            models.UniqueConstraint(
                fields=["base_conocimiento", "nombre"],
                name="unique_regla_nombre_por_base",
            ),
            models.CheckConstraint(
                condition=Q(prioridad__gte=0),
                name="chk_regla_prioridad_no_negativa",
            ),
            models.CheckConstraint(
                condition=Q(factor_certeza__isnull=True)
                | (Q(factor_certeza__gte=0) & Q(factor_certeza__lte=1)),
                name="chk_regla_factor_certeza_rango_cero_uno",
            ),
        ]
        ordering = ["-prioridad", "nombre"]

    def __str__(self):
        return f"Regla: {self.nombre} (P: {self.prioridad})"


class CondicionModel(models.Model):
    """Modelo ORM para una Condición de una Regla."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    regla = models.ForeignKey(
        ReglaModel,
        on_delete=models.CASCADE,
        related_name="condiciones",
        verbose_name="Regla",
    )
    variable = models.ForeignKey(
        VariableModel,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="condiciones",
        verbose_name="Variable evaluada",
    )
    hecho = models.ForeignKey(
        HechoModel,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="condiciones",
        verbose_name="Hecho evaluado",
    )
    operador = models.CharField(
        max_length=20,
        choices=OperadorCondicion.choices(),
        verbose_name="Operador",
    )
    valor_esperado = models.CharField(max_length=255, verbose_name="Valor esperado")
    orden = models.PositiveIntegerField(default=1, verbose_name="Orden de evaluación")

    class Meta:
        db_table = "condiciones"
        verbose_name = "Condición"
        verbose_name_plural = "Condiciones"
        ordering = ["orden"]

    def __str__(self):
        sujeto = (
            self.variable.nombre
            if self.variable
            else (self.hecho.nombre if self.hecho else "N/A")
        )
        return f"{sujeto} {self.operador} {self.valor_esperado}"


class ConclusionModel(models.Model):
    """Modelo ORM para una Conclusión resultante de una Regla."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    regla = models.ForeignKey(
        ReglaModel,
        on_delete=models.CASCADE,
        related_name="conclusiones",
        verbose_name="Regla",
    )
    hecho_resultante = models.ForeignKey(
        HechoModel,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="conclusiones_resultantes",
        verbose_name="Hecho resultante",
    )
    variable_resultante = models.ForeignKey(
        VariableModel,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="conclusiones_resultantes",
        verbose_name="Variable resultante",
    )
    valor_resultante = models.CharField(max_length=255, verbose_name="Valor resultante")

    class Meta:
        db_table = "conclusiones"
        verbose_name = "Conclusión"
        verbose_name_plural = "Conclusiones"

    def __str__(self):
        destino = (
            self.variable_resultante.nombre
            if self.variable_resultante
            else (self.hecho_resultante.nombre if self.hecho_resultante else "N/A")
        )
        return f"Conclusión -> {destino} = {self.valor_resultante}"
