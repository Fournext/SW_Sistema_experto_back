"""
Entidades de dominio para la Validación de Bases de Conocimiento (Sprint 2 - HU-18, HU-19).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from compartido.constantes.enums import SeveridadIncidencia, TipoIncidencia


@dataclass
class IncidenciaValidacion:
    """Entidad que describe una anomalía o inconsistencia detectada en la base."""

    id: UUID = field(default_factory=uuid4)
    validacion_id: Optional[UUID] = None
    codigo: str = ""
    tipo: str = TipoIncidencia.ESTRUCTURAL.value
    severidad: str = SeveridadIncidencia.ERROR.value
    entidad_tipo: str = "REGLA"
    entidad_id: Optional[UUID] = None
    entidad_nombre: Optional[str] = None
    descripcion: str = ""
    posible_causa: str = ""
    sugerencia: str = ""
    creada_en: Optional[datetime] = None


@dataclass
class ResultadoValidacion:
    """Resultado del análisis completo de una base de conocimiento."""

    id: UUID = field(default_factory=uuid4)
    base_conocimiento_id: Optional[UUID] = None
    fecha_validacion: Optional[datetime] = None
    es_valida: bool = True
    total_errores: int = 0
    total_advertencias: int = 0
    resumen: str = ""
    incidencias: List[IncidenciaValidacion] = field(default_factory=list)
