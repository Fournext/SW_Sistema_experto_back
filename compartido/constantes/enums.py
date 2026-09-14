"""
Enumeraciones y constantes compartidas para el sistema experto.
"""
try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self):
            return str(self.value)


class EstadoSistema(StrEnum):
    BORRADOR = "BORRADOR"
    ACTIVO = "ACTIVO"
    ARCHIVADO = "ARCHIVADO"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class TipoDato(StrEnum):
    TEXTO = "TEXTO"
    ENTERO = "ENTERO"
    DECIMAL = "DECIMAL"
    BOOLEANO = "BOOLEANO"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class OperadorCondicion(StrEnum):
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


class TipoNodoVisual(StrEnum):
    HECHO = "HECHO"
    VARIABLE = "VARIABLE"
    CONDICION = "CONDICION"
    REGLA = "REGLA"
    CONCLUSION = "CONCLUSION"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class EstadoEjecucion(StrEnum):
    INICIADA = "INICIADA"
    EJECUTANDO = "EJECUTANDO"
    FINALIZADA = "FINALIZADA"
    ERROR = "ERROR"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class EstadoReglaInferencia(StrEnum):
    EVALUADA = "EVALUADA"
    RECHAZADA = "RECHAZADA"
    ACTIVADA = "ACTIVADA"
    EJECUTADA = "EJECUTADA"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]
