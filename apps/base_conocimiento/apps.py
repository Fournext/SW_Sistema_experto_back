from django.apps import AppConfig


class BaseConocimientoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.base_conocimiento"
    verbose_name = "Base de Conocimiento"
