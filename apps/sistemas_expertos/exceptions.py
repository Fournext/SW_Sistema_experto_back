"""
Excepciones de dominio específicas para el módulo de Sistemas Expertos.
"""
from compartido.excepciones.base import ExcepcionEntidadNoEncontrada, ExcepcionValidacionDominio


class SistemaExpertoNoEncontrado(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_sistema=None):
        if id_sistema:
            mensaje = f"No se encontró el sistema experto con ID: {id_sistema}"
        else:
            mensaje = "Sistema experto no encontrado."
        super().__init__(mensaje, {"id": [mensaje]})


class NombreSistemaExpertoRequerido(ExcepcionValidacionDominio):
    def __init__(self):
        super().__init__(
            "El nombre del sistema experto es obligatorio.",
            {"nombre": ["Este campo no puede estar vacío."]},
        )
