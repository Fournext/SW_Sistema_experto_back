"""
Validadores de dominio para la Base de Conocimiento.
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from apps.base_conocimiento.exceptions import (
    ConclusionReferenciaInvalidaError,
    CondicionReferenciaInvalidaError,
    FactorCertezaInvalidoError,
    PrioridadInvalidaError,
    TipoDatoInvalidoError,
)
from compartido.constantes.enums import TipoDato


class ValidadorBaseConocimiento:
    """Validador transversal de componentes de la base de conocimiento."""

    @staticmethod
    def validar_tipo_dato(tipo: str) -> None:
        try:
            TipoDato(tipo)
        except ValueError:
            raise TipoDatoInvalidoError(tipo)

    @staticmethod
    def validar_prioridad(prioridad: int) -> None:
        if prioridad is None or prioridad < 0:
            raise PrioridadInvalidaError()

    @staticmethod
    def validar_factor_certeza(factor: Optional[Decimal]) -> None:
        if factor is not None:
            if factor < Decimal("0.0") or factor > Decimal("1.0"):
                raise FactorCertezaInvalidoError()

    @staticmethod
    def validar_referencia_condicion(
        variable_id: Optional[UUID], hecho_id: Optional[UUID]
    ) -> None:
        tiene_variable = variable_id is not None
        tiene_hecho = hecho_id is not None
        # Exclusividad estricta: XOR
        if not (tiene_variable ^ tiene_hecho):
            raise CondicionReferenciaInvalidaError()

    @staticmethod
    def validar_destino_conclusion(
        hecho_id: Optional[UUID], variable_id: Optional[UUID]
    ) -> None:
        tiene_hecho = hecho_id is not None
        tiene_variable = variable_id is not None
        # Exclusividad estricta: XOR
        if not (tiene_hecho ^ tiene_variable):
            raise ConclusionReferenciaInvalidaError()
