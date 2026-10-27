"""
Entidades de dominio para la persistencia del histórico y simulación de Inferencia (Sprint 1 + Sprint 2).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from compartido.constantes.enums import (
    EstadoEjecucion,
    EstadoReglaInferencia,
    ModoInferencia,
    ProcedenciaHecho,
    TipoDato,
)


@dataclass
class DetalleInferencia:
    """Entidad que registra un paso en la traza de la inferencia (Sprint 1)."""

    id: UUID = field(default_factory=uuid4)
    ejecucion_id: Optional[UUID] = None
    regla_id: Optional[UUID] = None
    orden: int = 1
    estado_regla: EstadoReglaInferencia = EstadoReglaInferencia.EVALUADA
    condiciones_cumplidas: Optional[bool] = None
    resultado_generado: Optional[str] = None
    condiciones_evaluadas: List[Dict[str, Any]] = field(default_factory=list)
    paso_numero: Optional[int] = None
    paso_visual: Optional[int] = None


@dataclass
class PasoInferencia:
    """Entidad que representa un paso discreto ejecutado (Sprint 2 - HU-09)."""

    id: UUID = field(default_factory=uuid4)
    ejecucion_id: Optional[UUID] = None
    numero_paso: int = 1
    regla_disparada_id: Optional[UUID] = None
    regla_nombre: Optional[str] = None
    memoria_trabajo_pre: Dict[str, Any] = field(default_factory=dict)
    memoria_trabajo_post: Dict[str, Any] = field(default_factory=dict)
    descripcion: str = ""
    fecha_ejecucion: Optional[datetime] = None


@dataclass
class HechoInferido:
    """Entidad que representa un hecho generado/derivado (Sprint 2 - HU-12)."""

    id: UUID = field(default_factory=uuid4)
    ejecucion_id: Optional[UUID] = None
    paso_id: Optional[UUID] = None
    regla_origen_id: Optional[UUID] = None
    regla_origen_nombre: Optional[str] = None
    nombre: str = ""
    valor: str = ""
    tipo_dato: str = TipoDato.TEXTO.value
    procedencia: str = ProcedenciaHecho.DERIVADO.value
    orden: int = 1
    creado_en: Optional[datetime] = None


@dataclass
class ConflictoReglaCandidata:
    """Candidata en un conjunto de conflicto (Sprint 2 - HU-13)."""

    id: UUID = field(default_factory=uuid4)
    conflicto_id: Optional[UUID] = None
    regla_id: Optional[UUID] = None
    regla_nombre: str = ""
    prioridad: int = 0
    fue_seleccionada: bool = False
    motivo_descarte: Optional[str] = None


@dataclass
class ConflictoInferencia:
    """Conjunto de conflicto registrado en un paso de inferencia (Sprint 2 - HU-13)."""

    id: UUID = field(default_factory=uuid4)
    ejecucion_id: Optional[UUID] = None
    paso_id: Optional[UUID] = None
    numero_paso: int = 1
    regla_seleccionada_id: Optional[UUID] = None
    regla_seleccionada_nombre: str = ""
    criterio_aplicado: str = "PRIORIDAD_DESC_ESPECIFICIDAD_ID"
    explicacion_resolucion: str = ""
    reglas_candidatas: List[ConflictoReglaCandidata] = field(default_factory=list)
    creado_en: Optional[datetime] = None


@dataclass
class ExplicacionConclusion:
    """Estructura de explicabilidad causal de una conclusión (Sprint 2 - HU-17)."""

    id: UUID = field(default_factory=uuid4)
    ejecucion_id: Optional[UUID] = None
    conclusion: str = ""
    arbol_justificacion: Dict[str, Any] = field(default_factory=dict)
    texto_explicativo: str = ""
    creada_en: Optional[datetime] = None


@dataclass
class EjecucionInferencia:
    """Entidad que representa una corrida o sesión del motor de inferencia."""

    id: UUID = field(default_factory=uuid4)
    asignacion_id: Optional[UUID] = None
    estudiante_id: Optional[int] = None
    bc_snapshot: Dict[str, Any] = field(default_factory=dict)
    sistema_experto_id: Optional[UUID] = None
    estado: EstadoEjecucion = EstadoEjecucion.INICIADA
    modo: ModoInferencia = ModoInferencia.AUTOMATICA
    paso_actual: int = 0
    memoria_trabajo_snapshot: Dict[str, Any] = field(default_factory=dict)
    hechos_iniciales_snapshot: List[Dict[str, Any]] = field(default_factory=list)
    recorrido_por_regla: Dict[str, Any] = field(default_factory=dict)
    es_simulacion: bool = False
    total_pasos: Optional[int] = None
    total_reglas_evaluadas: Optional[int] = None
    total_reglas_disparadas: Optional[int] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    conclusion_final: Optional[str] = None
    detalles: List[DetalleInferencia] = field(default_factory=list)
    pasos: List[PasoInferencia] = field(default_factory=list)
    hechos_inferidos: List[HechoInferido] = field(default_factory=list)
    conflictos: List[ConflictoInferencia] = field(default_factory=list)
    explicacion: Optional[ExplicacionConclusion] = None
