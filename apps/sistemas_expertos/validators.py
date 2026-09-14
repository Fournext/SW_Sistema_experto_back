"""
Validadores de dominio para Sistemas Expertos.
"""
from apps.sistemas_expertos.exceptions import NombreSistemaExpertoRequerido


class ValidadorSistemaExperto:
    """Valida reglas de negocio del Sistema Experto."""

    @staticmethod
    def validar_nombre(nombre: str) -> None:
        if not nombre or not nombre.strip():
            raise NombreSistemaExpertoRequerido()
