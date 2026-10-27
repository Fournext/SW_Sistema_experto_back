"""
Objetos de valor y estructuras para la traza de ejecución del motor de inferencia (Sprint 1 + Sprint 2).
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
    condiciones_evaluadas: List[Dict[str, Any]] = field(default_factory=list)
    paso_numero: Optional[int] = None
    paso_visual: Optional[int] = None


@dataclass
class PasoEjecucionResultado:
    """Resultado de la ejecución de un paso individual en modo paso a paso o simulación."""

    numero_paso: int
    finalizado: bool
    memoria_trabajo_pre: Dict[str, Any]
    memoria_trabajo_post: Dict[str, Any]
    regla_disparada: Optional[Any] = None
    candidatas_conflicto: List[Any] = field(default_factory=list)
    hechos_generados: List[Dict[str, Any]] = field(default_factory=list)
    trazas_paso: List[EntradaTraza] = field(default_factory=list)
    criterio_conflicto: str = ""
    explicacion_conflicto: str = ""
    motivos_descarte_conflicto: Dict[UUID, str] = field(default_factory=dict)
    conclusion_final: Optional[str] = None
    descripcion: str = ""


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
    pasos: List[PasoEjecucionResultado] = field(default_factory=list)
