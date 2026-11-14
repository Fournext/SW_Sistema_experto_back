import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from ..exceptions import RuntimeLaboratorioError


@dataclass
class VariableRef:
    id: str
    nombre: str
    tipo_dato: str = "TEXTO"
    es_nativa: bool = False

    def to_dict(self) -> dict:
        return {
            "tipo_objeto": "Variable",
            "id": self.id,
            "nombre": self.nombre,
            "tipo_dato": self.tipo_dato,
            "es_nativa": self.es_nativa,
        }


@dataclass
class HechoValor:
    id: str = ""
    variable_id: str = ""
    variable_nombre: str = ""
    valor: Any = None
    tipo_dato: str = "TEXTO"
    origen: str = "INICIAL"

    def __init__(
        self,
        id: str = "",
        variable_id: str = "",
        variable_nombre: str = "",
        valor: Any = None,
        tipo_dato: str = "TEXTO",
        variable: Optional[str] = None,
        origen: str = "INICIAL",
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.variable_id = variable_id or str(uuid.uuid4())[:8]
        self.variable_nombre = variable if variable is not None else variable_nombre
        self.valor = valor
        self.tipo_dato = tipo_dato
        self.origen = origen

    @property
    def variable(self) -> str:
        return self.variable_nombre

    @variable.setter
    def variable(self, val: str):
        self.variable_nombre = val

    def to_dict(self) -> dict:
        return {
            "tipo_objeto": "Hecho",
            "id": self.id,
            "variable_id": self.variable_id,
            "variable_nombre": self.variable_nombre,
            "variable": self.variable_nombre,
            "valor": self.valor,
            "tipo_dato": self.tipo_dato,
            "origen": self.origen,
        }


@dataclass
class ReglaRef:
    id: str
    nombre: str
    orden: int = 0
    condiciones_resumen: str = ""
    conclusion_resumen: str = ""
    premisas: List[dict] = field(default_factory=list)
    conclusiones: List[dict] = field(default_factory=list)
    marcada: bool = False
    disparada: bool = False

    def to_dict(self) -> dict:
        return {
            "tipo_objeto": "Regla",
            "id": self.id,
            "nombre": self.nombre,
            "orden": self.orden,
            "condiciones": self.condiciones_resumen,
            "conclusion": self.conclusion_resumen,
            "premisas": self.premisas,
            "conclusiones": self.conclusiones,
            "marcada": self.marcada,
            "disparada": self.disparada,
        }


def valores_son_iguales(a: Any, b: Any) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False

    # Comparación de referencias de dominio por ID
    if isinstance(a, (VariableRef, HechoValor, ReglaRef)) and isinstance(b, (VariableRef, HechoValor, ReglaRef)):
        if type(a) is not type(b):
            return False
        if isinstance(a, HechoValor):
            return a.variable_nombre == b.variable_nombre and str(a.valor).strip().lower() == str(b.valor).strip().lower()
        return a.id == b.id

    # Comparación de números con promoción int/double
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b

    return a == b


@dataclass
class ListaValue:
    elementos: List[Any] = field(default_factory=list)

    def add(self, elem: Any) -> bool:
        if self.contains(elem):
            return False
        self.elementos.append(elem)
        return True

    def contains(self, elem: Any) -> bool:
        for x in self.elementos:
            if valores_son_iguales(x, elem):
                return True
        return False

    def delete(self, elem: Any) -> bool:
        for i, x in enumerate(self.elementos):
            if valores_son_iguales(x, elem):
                self.elementos.pop(i)
                return True
        return False

    def get(self, indice: int) -> Any:
        if indice < 0 or indice >= len(self.elementos):
            raise RuntimeLaboratorioError(f"Índice fuera de rango en Lista: {indice}", codigo="INDICE_FUERA_RANGO")
        return self.elementos[indice]

    def length(self) -> int:
        return len(self.elementos)

    def vacia(self) -> bool:
        return len(self.elementos) == 0

    def to_dict(self) -> dict:
        return {
            "tipo_objeto": "Lista",
            "elementos": [serializar_valor(e) for e in self.elementos]
        }


@dataclass
class PilaValue:
    elementos: List[Any] = field(default_factory=list)

    def push(self, elem: Any):
        self.elementos.append(elem)

    def pop(self) -> Any:
        if not self.elementos:
            raise RuntimeLaboratorioError("Intento de pop() en una Pila vacía.", codigo="ESTRUCTURA_VACIA")
        return self.elementos.pop()

    def length(self) -> int:
        return len(self.elementos)

    def vacia(self) -> bool:
        return len(self.elementos) == 0

    def to_dict(self) -> dict:
        return {
            "tipo_objeto": "Pila",
            "elementos": [serializar_valor(e) for e in self.elementos]
        }


@dataclass
class ColaValue:
    elementos: List[Any] = field(default_factory=list)

    def meter(self, elem: Any):
        self.elementos.append(elem)

    def pop(self) -> Any:
        if not self.elementos:
            raise RuntimeLaboratorioError("Intento de pop() en una Cola vacía.", codigo="ESTRUCTURA_VACIA")
        return self.elementos.pop(0)

    def length(self) -> int:
        return len(self.elementos)

    def vacia(self) -> bool:
        return len(self.elementos) == 0

    def to_dict(self) -> dict:
        return {
            "tipo_objeto": "Cola",
            "elementos": [serializar_valor(e) for e in self.elementos]
        }


@dataclass
class BaseHechosValue:
    # Mapea nombre_variable -> HechoValor
    hechos_por_var: Dict[str, HechoValor] = field(default_factory=dict)
    # Registro de variables consultadas al usuario (incluso si canceló o devolvió null)
    variables_consultadas: Set[str] = field(default_factory=set)

    def contains(self, variable: VariableRef) -> bool:
        return variable.nombre.strip().lower() in self.hechos_por_var

    def get(self, variable: VariableRef) -> Optional[HechoValor]:
        return self.hechos_por_var.get(variable.nombre.strip().lower())

    def add(self, hecho: HechoValor) -> bool:
        var_norm = hecho.variable_nombre.strip().lower()
        if var_norm in self.hechos_por_var:
            existente = self.hechos_por_var[var_norm]
            val_existente = str(existente.valor).strip().lower()
            val_nuevo = str(hecho.valor).strip().lower()
            if val_existente == val_nuevo:
                return False  # No-op, ya estaba unificado con el mismo valor
            # CONTRADICCIÓN: en la unificación determinista de clase, fijar X=80 y luego X=90 es contradicción
            raise RuntimeLaboratorioError(
                f"Contradicción en Base de Hechos: la variable '{hecho.variable_nombre}' ya está unificada con '{existente.valor}', no se puede asignar '{hecho.valor}'.",
                codigo="CONTRADICCION"
            )

        self.hechos_por_var[var_norm] = hecho
        return True

    def length(self) -> int:
        return len(self.hechos_por_var)

    def to_dict(self) -> dict:
        return {
            "tipo_objeto": "BaseHechos",
            "hechos": {k: v.to_dict() for k, v in self.hechos_por_var.items()},
            "consultadas": list(self.variables_consultadas),
        }


def serializar_valor(val: Any) -> Any:
    if val is None or isinstance(val, (int, float, bool, str)):
        return val
    if hasattr(val, "to_dict"):
        return val.to_dict()
    if isinstance(val, list):
        return [serializar_valor(x) for x in val]
    return str(val)


def deserializar_valor(val: Any) -> Any:
    if val is None or isinstance(val, (int, float, bool, str)):
        return val
    if isinstance(val, list):
        return [deserializar_valor(x) for x in val]
    if isinstance(val, dict):
        tipo_obj = val.get("tipo_objeto")
        if tipo_obj == "Variable":
            return VariableRef(
                id=val.get("id", ""),
                nombre=val.get("nombre", ""),
                tipo_dato=val.get("tipo_dato", "TEXTO"),
                es_nativa=val.get("es_nativa", False),
            )
        elif tipo_obj == "Hecho":
            return HechoValor(
                id=val.get("id", ""),
                variable_id=val.get("variable_id", ""),
                variable_nombre=val.get("variable_nombre", val.get("variable", "")),
                valor=val.get("valor"),
                tipo_dato=val.get("tipo_dato", "TEXTO"),
                origen=val.get("origen", "INICIAL"),
            )
        elif tipo_obj == "Regla":
            return ReglaRef(
                id=val.get("id", ""),
                nombre=val.get("nombre", ""),
                orden=val.get("orden", 0),
                condiciones_resumen=val.get("condiciones", ""),
                conclusion_resumen=val.get("conclusion", ""),
                premisas=val.get("premisas", []),
                conclusiones=val.get("conclusiones", []),
                marcada=val.get("marcada", False),
                disparada=val.get("disparada", False),
            )
        elif tipo_obj == "Lista":
            return ListaValue(elementos=[deserializar_valor(e) for e in val.get("elementos", [])])
        elif tipo_obj == "Pila":
            return PilaValue(elementos=[deserializar_valor(e) for e in val.get("elementos", [])])
        elif tipo_obj == "Cola":
            return ColaValue(elementos=[deserializar_valor(e) for e in val.get("elementos", [])])
        elif tipo_obj == "BaseHechos":
            bh = BaseHechosValue()
            for k, h_dict in val.get("hechos", {}).items():
                bh.hechos_por_var[k] = deserializar_valor(h_dict)
            bh.variables_consultadas = set(val.get("consultadas", []))
            return bh
        return {k: deserializar_valor(v) for k, v in val.items()}
    return val

