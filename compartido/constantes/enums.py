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
    OPCION = "OPCION"

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
    PAUSADA = "PAUSADA"
    FINALIZADA = "FINALIZADA"
    ERROR = "ERROR"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class ModoInferencia(StrEnum):
    AUTOMATICA = "AUTOMATICA"
    PASO_A_PASO = "PASO_A_PASO"
    SIMULACION = "SIMULACION"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class ProcedenciaHecho(StrEnum):
    INICIAL = "INICIAL"
    DERIVADO = "DERIVADO"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class SeveridadIncidencia(StrEnum):
    ERROR = "ERROR"
    ADVERTENCIA = "ADVERTENCIA"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class TipoIncidencia(StrEnum):
    ESTRUCTURAL = "ESTRUCTURAL"
    SEMANTICA = "SEMANTICA"
    REFERENCIAL = "REFERENCIAL"
    CICLO = "CICLO"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class DificultadActividad(StrEnum):
    BASICA = "BASICA"
    MEDIA = "MEDIA"
    AVANZADA = "AVANZADA"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class EstadoActividad(StrEnum):
    BORRADOR = "BORRADOR"
    PUBLICADA = "PUBLICADA"
    INACTIVA = "INACTIVA"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class EstadoAsignacion(StrEnum):
    VIGENTE = "VIGENTE"
    CERRADA = "CERRADA"

    @classmethod
    def choices(cls):
        return [(item.value, item.value) for item in cls]


class EstadoEntrega(StrEnum):
    BORRADOR = "BORRADOR"
    ENVIADA = "ENVIADA"

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

