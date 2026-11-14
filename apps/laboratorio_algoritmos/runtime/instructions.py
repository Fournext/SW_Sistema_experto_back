from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional
from ..exceptions import SourceSpan


class OpCode(Enum):
    # Paso visible en el depurador
    LINE_STEP = auto()

    # Literales y Pila
    CONST = auto()              # arg: valor primitivo
    POP = auto()
    DUP = auto()

    # Variables
    LOAD_VAR = auto()          # arg: nombre
    STORE_VAR = auto()         # arg: nombre
    UPDATE_VAR = auto()        # arg: (nombre, es_incremento)

    # Operadores
    BINARY_OP = auto()         # arg: operador str ('+', '==', etc.)
    UNARY_OP = auto()          # arg: operador str ('!', '-')

    # Colecciones y Objetos
    NEW_ARRAY = auto()         # arg: tipo_elemento
    NEW_COLLECTION = auto()    # arg: (tipo_coleccion, parametro_tipo)
    LOAD_INDEX = auto()
    STORE_INDEX = auto()
    LOAD_MEMBER = auto()       # arg: nombre_miembro
    STORE_MEMBER = auto()      # arg: nombre_miembro

    # Saltos
    JUMP = auto()              # arg: target_pc (int)
    JUMP_IF_FALSE = auto()     # arg: target_pc (int)
    JUMP_IF_TRUE = auto()      # arg: target_pc (int)

    # Funciones
    CALL = auto()              # arg: (nombre_funcion, arg_count)
    CALL_METHOD = auto()       # arg: (nombre_metodo, arg_count)
    RETURN = auto()            # arg: tiene_valor (bool)


@dataclass
class Instruction:
    op: OpCode
    arg: Any = None
    span: Optional[SourceSpan] = None

    def to_dict(self) -> dict:
        return {
            "op": self.op.name,
            "arg": str(self.arg) if self.arg is not None else None,
            "span": self.span.to_dict() if self.span else None,
        }

