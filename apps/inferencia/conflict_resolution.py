"""
Estrategias para la resolución de conflictos en el motor de inferencia.
Cuando múltiples reglas pueden dispararse (conjunto de conflicto), se selecciona una según la estrategia.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List
from uuid import UUID
from apps.base_conocimiento.entities import Regla


@dataclass
class ResultadoConflicto:
    """Resultado detallado de la resolución del conjunto de conflicto."""

    regla_ganadora: Regla
    candidatas: List[Regla]
    criterio_aplicado: str
    explicacion_resolucion: str
    motivos_descarte: Dict[UUID, str] = field(default_factory=dict)


class EstrategiaResolucionConflictos(ABC):
    """Abstracción base para resolución de conflictos del conjunto de conflicto."""

    @abstractmethod
    def resolver(self, reglas: List[Regla]) -> Regla:
        """Selecciona una única regla ganadora del conjunto de conflicto."""
        pass

    @abstractmethod
    def resolver_con_detalle(self, reglas: List[Regla]) -> ResultadoConflicto:
        """Selecciona la regla ganadora y genera la justificación de descarte de las demás."""
        pass


class ResolucionPorPrioridad(EstrategiaResolucionConflictos):
    """
    Estrategia de resolución determinista:
    1. Mayor prioridad numérica (descendente).
    2. Mayor especificidad (número de condiciones satisfechas, descendente).
    3. Desempate lexicográfico por UUID (ascendente) para garantizar determinismo estricto.
    """

    def resolver(self, reglas: List[Regla]) -> Regla:
        res = self.resolver_con_detalle(reglas)
        return res.regla_ganadora

    def resolver_con_detalle(self, reglas: List[Regla]) -> ResultadoConflicto:
        if not reglas:
            raise ValueError("El conjunto de conflicto está vacío.")

        # Ordenamiento determinista multi-criterio
        reglas_ordenadas = sorted(
            reglas,
            key=lambda r: (-r.prioridad, -len(r.condiciones or []), str(r.id)),
        )
        ganadora = reglas_ordenadas[0]

        criterio = "PRIORIDAD_DESC_ESPECIFICIDAD_ID"
        motivos: Dict[UUID, str] = {}
        for r in reglas_ordenadas[1:]:
            if r.prioridad < ganadora.prioridad:
                motivos[r.id] = (
                    f"Menor prioridad ({r.prioridad} frente a {ganadora.prioridad} de '{ganadora.nombre}')"
                )
            elif len(r.condiciones or []) < len(ganadora.condiciones or []):
                motivos[r.id] = (
                    f"Misma prioridad ({r.prioridad}), pero menor especificidad "
                    f"({len(r.condiciones or [])} condiciones vs {len(ganadora.condiciones or [])})"
                )
            else:
                motivos[r.id] = (
                    f"Empate en prioridad y especificidad; desempatada por identificador estable ({str(r.id)[:8]}...)"
                )

        explicacion = (
            f"Se seleccionó la regla '{ganadora.nombre}' por tener la mayor prioridad ({ganadora.prioridad}) "
            f"y {len(ganadora.condiciones or [])} condición(es)."
        )

        return ResultadoConflicto(
            regla_ganadora=ganadora,
            candidatas=reglas,
            criterio_aplicado=criterio,
            explicacion_resolucion=explicacion,
            motivos_descarte=motivos,
        )
