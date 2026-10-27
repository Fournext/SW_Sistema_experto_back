from django.db import models


class Permiso(models.Model):
    """
    Modelo gestor para los permisos del catálogo del sistema.
    managed = False para no generar tablas innecesarias: los permisos
    reales se almacenan directamente en django.contrib.auth.models.Permission
    asociados al ContentType de este modelo.
    """

    class Meta:
        managed = False
        default_permissions = ()
        verbose_name = "Permiso del Sistema"
        verbose_name_plural = "Permisos del Sistema"
