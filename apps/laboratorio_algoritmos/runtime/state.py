from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from .values import serializar_valor, deserializar_valor


@dataclass
class StackFrame:
    nombre_funcion: str
    pc: int = 0
    variables: Dict[str, Any] = field(default_factory=dict)
    pila_operandos: List[Any] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nombre_funcion": self.nombre_funcion,
            "pc": self.pc,
            "variables": {k: serializar_valor(v) for k, v in self.variables.items()},
            "pila_operandos": [serializar_valor(v) for v in self.pila_operandos],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StackFrame":
        return cls(
            nombre_funcion=data.get("nombre_funcion", "main"),
            pc=data.get("pc", 0),
            variables={k: deserializar_valor(v) for k, v in data.get("variables", {}).items()},
            pila_operandos=[deserializar_valor(v) for v in data.get("pila_operandos", [])],
        )


@dataclass
class EventoTraza:
    tipo: str               # PASO, EVALUACION_REGLA, HECHO_AGREGADO, REGLA_MARCADA, CONSULTA_SOLICITADA, SALIDA_TEXTO
    descripcion: str
    datos: Dict[str, Any] = field(default_factory=dict)
    pc: int = 0
    linea: int = 0
    columna: int = 0

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "descripcion": self.descripcion,
            "datos": self.datos,
            "pc": self.pc,
            "linea": self.linea,
            "columna": self.columna,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventoTraza":
        return cls(
            tipo=data.get("tipo", "PASO"),
            descripcion=data.get("descripcion", ""),
            datos=data.get("datos", {}),
            pc=data.get("pc", 0),
            linea=data.get("linea", 0),
            columna=data.get("columna", 0),
        )


@dataclass
class PreguntaPendiente:
    id_pregunta: str
    variable_id: str
    variable_nombre: str
    texto: str

    def to_dict(self) -> dict:
        return {
            "id_pregunta": self.id_pregunta,
            "variable_id": self.variable_id,
            "variable_nombre": self.variable_nombre,
            "texto": self.texto,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PreguntaPendiente":
        return cls(
            id_pregunta=data.get("id_pregunta", ""),
            variable_id=data.get("variable_id", ""),
            variable_nombre=data.get("variable_nombre", ""),
            texto=data.get("texto", ""),
        )


@dataclass
class VMState:
    frames: List[StackFrame] = field(default_factory=list)
    marcas_reglas: Set[str] = field(default_factory=set)
    estado: str = "LISTA"   # LISTA, EJECUTANDO, ESPERANDO_ENTRADA, FINALIZADA, ERROR, LIMITE_ALCANZADO
    pregunta_pendiente: Optional[PreguntaPendiente] = None
    eventos: List[EventoTraza] = field(default_factory=list)
    pasos_visibles: int = 0
    instrucciones_totales: int = 0
    salidas_texto: List[str] = field(default_factory=list)
    error_detalle: Optional[dict] = None

    def frame_actual(self) -> StackFrame:
        if not self.frames:
            raise RuntimeError("La pila de llamadas de la VM está vacía.")
        return self.frames[-1]

    def to_dict(self) -> dict:
        return {
            "estado": self.estado,
            "pasos_visibles": self.pasos_visibles,
            "instrucciones_totales": self.instrucciones_totales,
            "marcas_reglas": list(self.marcas_reglas),
            "pregunta_pendiente": self.pregunta_pendiente.to_dict() if self.pregunta_pendiente else None,
            "frames": [f.to_dict() for f in self.frames],
            "eventos": [e.to_dict() for e in self.eventos[-100:]],  # Últimos 100 eventos para resumen
            "salidas_texto": self.salidas_texto,
            "error_detalle": self.error_detalle,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VMState":
        preg_data = data.get("pregunta_pendiente")
        pregunta = PreguntaPendiente.from_dict(preg_data) if preg_data else None
        return cls(
            frames=[StackFrame.from_dict(f) for f in data.get("frames", [])],
            marcas_reglas=set(data.get("marcas_reglas", [])),
            estado=data.get("estado", "LISTA"),
            pregunta_pendiente=pregunta,
            eventos=[EventoTraza.from_dict(e) for e in data.get("eventos", [])],
            pasos_visibles=data.get("pasos_visibles", 0),
            instrucciones_totales=data.get("instrucciones_totales", 0),
            salidas_texto=data.get("salidas_texto", []),
            error_detalle=data.get("error_detalle"),
        )

