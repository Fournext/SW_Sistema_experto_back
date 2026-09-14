"""
Objetos de valor y estructuras para la traza de ejecución del motor de inferencia.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID
from compartido.constantes.enums import EstadoEjecucion, EstadoReglaInferencia


@dataclass
class EntradaTraza:
    """Detalle del paso de evaluación/activación/ejecución de una regla."""

    regla_id: UUID
    regla_nombre: str
    orden: int
    estado: EstadoReglaInferencia
    condiciones_cumplidas: Optional[bool] = None
    resultado_generado: Optional[str] = None


@dataclass
class ResultadoInferencia:
    """Resultado consolidado tras la ejecución completa del motor de inferencia."""

    ejecucion_id: Optional[UUID] = None
    estado: EstadoEjecucion = EstadoEjecucion.FINALIZADA
    hechos_iniciales: List[Dict[str, Any]] = field(default_factory=list)
    hechos_generados: List[Dict[str, Any]] = field(default_factory=list)
    reglas_evaluadas: List[EntradaTraza] = field(default_factory=list)
    conclusion_final: Optional[str] = None
    total_iteraciones: int = 0
