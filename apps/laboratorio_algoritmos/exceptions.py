from dataclasses import dataclass
from typing import Optional


@dataclass
class SourceSpan:
    line: int
    column: int
    offset_start: int
    offset_end: int

    @property
    def offset(self) -> int:
        return self.offset_start

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "column": self.column,
            "offset_start": self.offset_start,
            "offset_end": self.offset_end,
            "offset": self.offset_start,
        }


class LaboratorioError(Exception):
    """Excepción base para todos los errores del laboratorio de algoritmos."""
    def __init__(self, mensaje: str, span: Optional[SourceSpan] = None, codigo: str = "ERROR_GENERAL"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.span = span
        self.codigo = codigo

    def to_dict(self) -> dict:
        return {
            "codigo": self.codigo,
            "mensaje": self.mensaje,
            "span": self.span.to_dict() if self.span else None,
        }


class SintaxisError(LaboratorioError):
    """Error léxico o de sintaxis durante el parsing."""
    def __init__(self, mensaje: str, span: Optional[SourceSpan] = None, codigo: str = "ERROR_SINTAXIS"):
        super().__init__(mensaje, span, codigo)


class TipoError(LaboratorioError):
    """Error estático de tipos, ámbitos o firmas."""
    def __init__(self, mensaje: str, span: Optional[SourceSpan] = None, codigo: str = "ERROR_TIPO"):
        super().__init__(mensaje, span, codigo)


class RuntimeLaboratorioError(LaboratorioError):
    """Error dinámico durante la ejecución de la VM."""
    def __init__(self, mensaje: str, span: Optional[SourceSpan] = None, codigo: str = "ERROR_RUNTIME"):
        super().__init__(mensaje, span, codigo)
