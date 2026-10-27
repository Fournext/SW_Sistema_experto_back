"""
Entidades de dominio para la Base de Conocimiento.
Objetos puros de Python.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4
from compartido.constantes.enums import TipoDato, OperadorCondicion


@dataclass
class Hecho:
    """Representa un hecho atómico comprobado en la base de conocimiento."""

    id: UUID = field(default_factory=uuid4)
    base_conocimiento_id: Optional[UUID] = None
    nombre: str = ""
    valor: Optional[str] = None
    tipo_dato: TipoDato = TipoDato.TEXTO
    opciones: List[str] = field(default_factory=list)
    pregunta: Optional[str] = None
    es_inicial: bool = True


@dataclass
class Variable:
    """Representa una variable o atributo parametrizable en la base de conocimiento."""

    id: UUID = field(default_factory=uuid4)
    base_conocimiento_id: Optional[UUID] = None
    nombre: str = ""
    tipo_dato: TipoDato = TipoDato.TEXTO
    valor_defecto: Optional[str] = None
    pregunta: Optional[str] = None
    es_inicial: bool = False
    descripcion: Optional[str] = None


@dataclass
class Condicion:
    """Representa una condición (premisa) de una regla de producción."""

    id: UUID = field(default_factory=uuid4)
    regla_id: Optional[UUID] = None
    variable_id: Optional[UUID] = None
    hecho_id: Optional[UUID] = None
    operador: OperadorCondicion = OperadorCondicion.IGUAL
    valor_esperado: str = ""
    orden: int = 1


@dataclass
class Conclusion:
    """Representa la conclusión o acción consecuente generada por una regla."""

    id: UUID = field(default_factory=uuid4)
    regla_id: Optional[UUID] = None
    hecho_resultante_id: Optional[UUID] = None
    variable_resultante_id: Optional[UUID] = None
    valor_resultante: str = ""


@dataclass
class Regla:
    """Representa una regla SI-ENTONCES de producción en la base de conocimiento."""

    id: UUID = field(default_factory=uuid4)
    base_conocimiento_id: Optional[UUID] = None
    nombre: str = ""
    descripcion: Optional[str] = None
    prioridad: int = 0
    factor_certeza: Optional[Decimal] = None
    activa: bool = True
    condiciones: List[Condicion] = field(default_factory=list)
    conclusiones: List[Conclusion] = field(default_factory=list)


@dataclass
class BaseConocimiento:
    """Entidad agregada raíz que agrupa hechos, variables y reglas."""

    id: UUID = field(default_factory=uuid4)
    sistema_experto_id: Optional[UUID] = None
    nombre: str = ""
    version: int = 1
    creada_en: Optional[datetime] = None
    actualizada_en: Optional[datetime] = None
    hechos: List[Hecho] = field(default_factory=list)
    variables: List[Variable] = field(default_factory=list)
    reglas: List[Regla] = field(default_factory=list)
