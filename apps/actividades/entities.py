"""
Entidades de dominio para el módulo de Actividades Educativas (Sprint 2 - HU-23, HU-24, HU-25).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from compartido.constantes.enums import (
    DificultadActividad,
    EstadoActividad,
    EstadoAsignacion,
    EstadoEntrega,
)


@dataclass
class Curso:
    """Entidad mínima para un curso académico."""

    id: UUID = field(default_factory=uuid4)
    codigo: str = ""
    nombre: str = ""
    descripcion: Optional[str] = None
    docente_id: int = 1
    activo: bool = True
    creado_en: Optional[datetime] = None


@dataclass
class ActividadEducativa:
    """Entidad que representa una actividad de aprendizaje creada por un docente (HU-23)."""

    id: UUID = field(default_factory=uuid4)
    docente_id: int = 1
    docente_username: Optional[str] = None
    sistema_experto_id: Optional[UUID] = None
    sistema_experto_nombre: Optional[str] = None
    titulo: str = ""
    instrucciones: str = ""
    dificultad: str = DificultadActividad.MEDIA.value
    estado: str = EstadoActividad.BORRADOR.value
    activa: bool = True
    creada_en: Optional[datetime] = None
    actualizada_en: Optional[datetime] = None


@dataclass
class AsignacionActividad:
    """Entidad de asignación de una actividad a un curso (HU-24)."""

    id: UUID = field(default_factory=uuid4)
    actividad_id: Optional[UUID] = None
    actividad_titulo: Optional[str] = None
    curso_id: Optional[UUID] = None
    curso_codigo: Optional[str] = None
    curso_nombre: Optional[str] = None
    fecha_asignacion: Optional[datetime] = None
    fecha_limite: Optional[datetime] = None
    estado: str = EstadoAsignacion.VIGENTE.value


@dataclass
class EntregaActividad:
    """Entidad que registra la solución o borrador de un estudiante (HU-25)."""

    id: UUID = field(default_factory=uuid4)
    asignacion_id: Optional[UUID] = None
    estudiante_id: int = 1
    estudiante_username: Optional[str] = None
    estado: str = EstadoEntrega.BORRADOR.value
    solucion_texto: Optional[str] = None
    hechos_ingresados: List[Dict[str, Any]] = field(default_factory=list)
    ejecucion_inferencia_id: Optional[UUID] = None
    fecha_envio: Optional[datetime] = None
    creada_en: Optional[datetime] = None
    actualizada_en: Optional[datetime] = None
