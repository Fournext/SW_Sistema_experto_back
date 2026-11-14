from dataclasses import dataclass
from enum import Enum, auto
from typing import Any
from ..exceptions import SourceSpan


class TokenType(Enum):
    # Tipos Primitivos y Dominio
    KW_INT = auto()
    KW_DOUBLE = auto()
    KW_BOOLEAN = auto()
    KW_STRING = auto()
    KW_VOID = auto()
    KW_REGLA = auto()
    KW_VARIABLE = auto()
    KW_HECHO = auto()
    KW_BASE_HECHOS = auto()
    KW_LISTA = auto()
    KW_PILA = auto()
    KW_COLA = auto()

    # Control de flujo
    KW_IF = auto()
    KW_ELSE = auto()
    KW_WHILE = auto()
    KW_FOR = auto()
    KW_BREAK = auto()
    KW_CONTINUE = auto()
    KW_RETURN = auto()
    KW_NEW = auto()

    # Literales
    KW_TRUE = auto()
    KW_FALSE = auto()
    KW_NULL = auto()
    IDENTIFIER = auto()
    INT_LITERAL = auto()
    DOUBLE_LITERAL = auto()
    STRING_LITERAL = auto()
    BOOLEAN_LITERAL = auto()

    # Operadores
    ASSIGN = auto()         # =
    PLUS = auto()           # +
    MINUS = auto()          # -
    STAR = auto()           # *
    SLASH = auto()          # /
    PERCENT = auto()        # %
    INCREMENT = auto()      # ++
    DECREMENT = auto()      # --

    # Comparación
    EQUAL_EQUAL = auto()    # ==
    BANG_EQUAL = auto()     # !=
    LESS = auto()           # <
    LESS_EQUAL = auto()     # <=
    GREATER = auto()        # >
    GREATER_EQUAL = auto()  # >=

    # Lógicos
    AND_AND = auto()        # &&
    OR_OR = auto()          # ||
    BANG = auto()           # !

    # Delimitadores
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    SEMICOLON = auto()      # ;
    COMMA = auto()          # ,
    DOT = auto()            # .

    EOF = auto()


PALABRAS_CLAVE = {
    "int": TokenType.KW_INT,
    "double": TokenType.KW_DOUBLE,
    "boolean": TokenType.KW_BOOLEAN,
    "String": TokenType.KW_STRING,
    "void": TokenType.KW_VOID,
    "Regla": TokenType.KW_REGLA,
    "Variable": TokenType.KW_VARIABLE,
    "Hecho": TokenType.KW_HECHO,
    "BaseHechos": TokenType.KW_BASE_HECHOS,
    "Lista": TokenType.KW_LISTA,
    "Pila": TokenType.KW_PILA,
    "Cola": TokenType.KW_COLA,
    "if": TokenType.KW_IF,
    "else": TokenType.KW_ELSE,
    "while": TokenType.KW_WHILE,
    "for": TokenType.KW_FOR,
    "break": TokenType.KW_BREAK,
    "continue": TokenType.KW_CONTINUE,
    "return": TokenType.KW_RETURN,
    "new": TokenType.KW_NEW,
    "true": TokenType.KW_TRUE,
    "false": TokenType.KW_FALSE,
    "null": TokenType.KW_NULL,
}


@dataclass
class Token:
    tipo: TokenType
    lexema: str
    valor: Any
    span: SourceSpan

    def __repr__(self) -> str:
        return f"Token({self.tipo.name}, '{self.lexema}', {self.valor}, {self.span.line}:{self.span.column})"
