"""
Excepciones de dominio para el Motor de Inferencia.
"""
from compartido.excepciones.base import (
    ExcepcionDominio,
    ExcepcionEntidadNoEncontrada,
    ExcepcionLimiteIteraciones,
)


class EjecucionInferenciaNoEncontrada(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_ejecucion=None):
        if id_ejecucion:
            msg = f"Ejecución de inferencia no encontrada (ID: {id_ejecucion})"
        else:
            msg = "Ejecución de inferencia no encontrada."
        super().__init__(msg, {"ejecucion": [msg]})


class LimiteIteracionesAlcanzado(ExcepcionLimiteIteraciones):
    def __init__(self, limite: int):
        super().__init__(
            f"Se alcanzó el límite máximo de iteraciones permitido ({limite}). Posible ciclo infinito detectado.",
            {"limite": [f"El motor superó las {limite} iteraciones máximas."]},
        )


class InferenciaError(ExcepcionDominio):
    def __init__(self, mensaje: str, errores=None):
        super().__init__(mensaje, errores or {"inferencia": [mensaje]})
