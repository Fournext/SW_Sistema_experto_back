from dataclasses import dataclass, field
from typing import List, Optional, Any
from ..exceptions import SourceSpan


@dataclass
class ASTNode:
    span: SourceSpan


@dataclass
class TypeNode(ASTNode):
    nombre_base: str                 # int, double, boolean, String, void, Regla, Variable, Hecho, BaseHechos, Lista, Pila, Cola
    es_arreglo: bool = False         # T[]
    parametro_tipo: Optional['TypeNode'] = None  # Para Lista<T>, Pila<T>, Cola<T>

    def __repr__(self) -> str:
        s = self.nombre_base
        if self.parametro_tipo:
            s += f"<{self.parametro_tipo}>"
        if self.es_arreglo:
            s += "[]"
        return s


@dataclass
class ParamNode(ASTNode):
    tipo: TypeNode
    nombre: str


@dataclass
class ExprNode(ASTNode):
    pass


@dataclass
class LiteralExprNode(ExprNode):
    valor: Any
    tipo_literal: str  # int, double, boolean, String, null


@dataclass
class IdentifierExprNode(ExprNode):
    nombre: str


@dataclass
class UnaryExprNode(ExprNode):
    operador: str      # -, !
    operando: ExprNode


@dataclass
class BinaryExprNode(ExprNode):
    izquierda: ExprNode
    operador: str      # +, -, *, /, %, ==, !=, <, <=, >, >=, &&, ||
    derecha: ExprNode


@dataclass
class CallExprNode(ExprNode):
    callee: ExprNode   # Puede ser un Identificador simple o un MemberAccess
    argumentos: List[ExprNode] = field(default_factory=list)


@dataclass
class MemberAccessExprNode(ExprNode):
    objeto: ExprNode
    miembro: str       # e.g. length, contains, add


@dataclass
class IndexExprNode(ExprNode):
    coleccion: ExprNode
    indice: ExprNode


@dataclass
class NewArrayExprNode(ExprNode):
    tipo_elemento: TypeNode
    tamano: ExprNode


@dataclass
class NewCollectionExprNode(ExprNode):
    tipo_coleccion: str  # Lista, Pila, Cola
    parametro_tipo: TypeNode


@dataclass
class StmtNode(ASTNode):
    pass


@dataclass
class BlockStmtNode(StmtNode):
    sentencias: List[StmtNode] = field(default_factory=list)


@dataclass
class VarDeclStmtNode(StmtNode):
    tipo: TypeNode
    nombre: str
    inicializador: Optional[ExprNode] = None


@dataclass
class AssignmentStmtNode(StmtNode):
    destino: ExprNode
    valor: ExprNode


@dataclass
class UpdateStmtNode(StmtNode):
    destino: ExprNode
    es_incremento: bool  # True para ++, False para --


@dataclass
class ExpressionStmtNode(StmtNode):
    expresion: ExprNode


@dataclass
class IfStmtNode(StmtNode):
    condicion: ExprNode
    rama_then: StmtNode
    rama_else: Optional[StmtNode] = None


@dataclass
class WhileStmtNode(StmtNode):
    condicion: ExprNode
    cuerpo: StmtNode


@dataclass
class ForStmtNode(StmtNode):
    inicializacion: Optional[StmtNode]
    condicion: Optional[ExprNode]
    actualizacion: Optional[StmtNode]
    cuerpo: StmtNode


@dataclass
class ReturnStmtNode(StmtNode):
    valor: Optional[ExprNode] = None


@dataclass
class BreakStmtNode(StmtNode):
    pass


@dataclass
class ContinueStmtNode(StmtNode):
    pass


@dataclass
class FunctionDefNode(ASTNode):
    tipo_retorno: TypeNode
    nombre: str
    parametros: List[ParamNode]
    cuerpo: BlockStmtNode


@dataclass
class ProgramNode(ASTNode):
    funciones: List[FunctionDefNode] = field(default_factory=list)

