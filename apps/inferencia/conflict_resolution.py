"""
Estrategias para la resolución de conflictos en el motor de inferencia.
Cuando múltiples reglas pueden dispararse (conjunto de conflicto), se selecciona una según la estrategia.
"""
from abc import ABC, abstractmethod
from typing import List
from apps.base_conocimiento.entities import Regla


class EstrategiaResolucionConflictos(ABC):
    """Abstracción base para resolución de conflictos del conjunto de conflicto."""

    @abstractmethod
    def resolver(self, reglas: List[Regla]) -> Regla:
        """Selecciona una única regla ganadora del conjunto de conflicto."""
        pass


class ResolucionPorPrioridad(EstrategiaResolucionConflictos):
    """
    Estrategia de resolución:
    1. Mayor prioridad primero (descendente).
    2. En caso de empate en prioridad, orden determinista por UUID (ascendente).
    """

    def resolver(self, reglas: List[Regla]) -> Regla:
        if not reglas:
            raise ValueError("El conjunto de conflicto está vacío.")

        reglas_ordenadas = sorted(
            reglas,
            key=lambda r: (-r.prioridad, str(r.id)),
        )
        return reglas_ordenadas[0]
