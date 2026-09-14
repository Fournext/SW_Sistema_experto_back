"""
Entidades de dominio para la persistencia del histórico de Inferencia.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from compartido.constantes.enums import EstadoEjecucion, EstadoReglaInferencia


@dataclass
class DetalleInferencia:
    """Entidad que registra un paso en la traza de la inferencia."""

    id: UUID = field(default_factory=uuid4)
    ejecucion_id: Optional[UUID] = None
    regla_id: Optional[UUID] = None
    orden: int = 1
    estado_regla: EstadoReglaInferencia = EstadoReglaInferencia.EVALUADA
    condiciones_cumplidas: Optional[bool] = None
    resultado_generado: Optional[str] = None


@dataclass
class EjecucionInferencia:
    """Entidad que representa una corrida o sesión del motor de inferencia."""

    id: UUID = field(default_factory=uuid4)
    sistema_experto_id: Optional[UUID] = None
    estado: EstadoEjecucion = EstadoEjecucion.INICIADA
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    conclusion_final: Optional[str] = None
    detalles: List[DetalleInferencia] = field(default_factory=list)
