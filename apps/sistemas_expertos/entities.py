"""
Entidades de dominio para Sistemas Expertos.
Objetos puros de Python sin dependencias directas de Django.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from compartido.constantes.enums import EstadoSistema


@dataclass
class SistemaExperto:
    """Entidad de dominio que representa un Sistema Experto."""

    id: UUID = field(default_factory=uuid4)
    nombre: str = ""
    descripcion: Optional[str] = None
    estado: EstadoSistema = EstadoSistema.BORRADOR
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None

    def activar(self) -> None:
        self.estado = EstadoSistema.ACTIVO

    def archivar(self) -> None:
        self.estado = EstadoSistema.ARCHIVADO

    def cambiar_a_borrador(self) -> None:
        self.estado = EstadoSistema.BORRADOR

    @property
    def esta_activo(self) -> bool:
        return self.estado == EstadoSistema.ACTIVO
