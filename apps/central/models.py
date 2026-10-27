from django.conf import settings
from django.db import models


class RegistroAcceso(models.Model):
    """
    Bitácora de accesos, intentos de login y eventos de seguridad
    auditados desde Admin Central.
    """
    EVENTOS = (
        ("login_ok", "Inicio de sesión exitoso"),
        ("login_fallido", "Intento de inicio fallido"),
        ("logout", "Cierre de sesión"),
        ("registro", "Autoregistro de estudiante"),
        ("sesion_revocada", "Sesión revocada administrativamente"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accesos",
        verbose_name="Usuario autenticado",
    )
    username_ingresado = models.CharField(
        max_length=150,
        verbose_name="Nombre de usuario ingresado",
    )
    evento = models.CharField(
        max_length=50,
        choices=EVENTOS,
        db_index=True,
        verbose_name="Tipo de evento",
    )
    ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP",
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="User Agent del navegador",
    )
    detalles = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Detalles o metadatos adicionales",
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Fecha y hora del evento",
    )

    class Meta:
        db_table = "central_registro_acceso"
        verbose_name = "Registro de Acceso"
        verbose_name_plural = "Bitácora de Accesos"
        ordering = ["-fecha"]

    def __str__(self) -> str:
        return f"[{self.fecha:%Y-%m-%d %H:%M:%S}] {self.evento} - {self.username_ingresado} ({self.ip or 'IP no detectada'})"
