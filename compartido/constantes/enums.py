"""
Enumeraciones y constantes compartidas para el sistema experto.
"""
from enum import Enum


class EstadoSistema(str, Enum):
    BORRADOR = "BORRADOR"
    ACTIVO = "ACTIVO"
    ARCHIVADO = "ARCHIVADO"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class TipoDato(str, Enum):
    TEXTO = "TEXTO"
    ENTERO = "ENTERO"
    DECIMAL = "DECIMAL"
    BOOLEANO = "BOOLEANO"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class OperadorCondicion(str, Enum):
    IGUAL = "="
    DISTINTO = "!="
    MAYOR = ">"
    MENOR = "<"
    MAYOR_IGUAL = ">="
    MENOR_IGUAL = "<="
    CONTIENE = "CONTIENE"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class TipoNodoVisual(str, Enum):
    HECHO = "HECHO"
    VARIABLE = "VARIABLE"
    CONDICION = "CONDICION"
    REGLA = "REGLA"
    CONCLUSION = "CONCLUSION"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class EstadoEjecucion(str, Enum):
    INICIADA = "INICIADA"
    EJECUTANDO = "EJECUTANDO"
    FINALIZADA = "FINALIZADA"
    ERROR = "ERROR"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class EstadoReglaInferencia(str, Enum):
    EVALUADA = "EVALUADA"
    RECHAZADA = "RECHAZADA"
    ACTIVADA = "ACTIVADA"
    EJECUTADA = "EJECUTADA"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]
