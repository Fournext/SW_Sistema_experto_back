"""
Entidades de dominio para el Editor Visual.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4
from compartido.constantes.enums import TipoNodoVisual


@dataclass
class NodoVisual:
    """Representa un nodo gráfico en el lienzo del docente."""

    id: UUID = field(default_factory=uuid4)
    sistema_experto_id: Optional[UUID] = None
    tipo: TipoNodoVisual = TipoNodoVisual.HECHO
    referencia_id: Optional[UUID] = None
    posicion_x: Decimal = Decimal("0.0")
    posicion_y: Decimal = Decimal("0.0")


@dataclass
class ConexionVisual:
    """Representa una arista o relación dirigida entre dos nodos del lienzo."""

    id: UUID = field(default_factory=uuid4)
    sistema_experto_id: Optional[UUID] = None
    nodo_origen_id: Optional[UUID] = None
    nodo_destino_id: Optional[UUID] = None
    etiqueta: Optional[str] = None
    tipo: Optional[str] = None
