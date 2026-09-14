"""
Excepciones de dominio para el Editor Visual.
"""
from compartido.excepciones.base import (
    ExcepcionEntidadNoEncontrada,
    ExcepcionValidacionDominio,
)


class NodoVisualNoEncontrado(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_nodo=None):
        msg = (
            f"Nodo visual no encontrado (ID: {id_nodo})"
            if id_nodo
            else "Nodo visual no encontrado."
        )
        super().__init__(msg, {"nodo": [msg]})


class ConexionVisualNoEncontrada(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_conexion=None):
        msg = (
            f"Conexión visual no encontrada (ID: {id_conexion})"
            if id_conexion
            else "Conexión visual no encontrada."
        )
        super().__init__(msg, {"conexion": [msg]})


class ConexionConsigoMismoError(ExcepcionValidacionDominio):
    def __init__(self):
        super().__init__(
            "Un nodo no puede conectarse consigo mismo (origen y destino deben ser distintos).",
            {"nodos": ["El nodo de origen no puede ser igual al nodo de destino."]},
        )


class ConexionDuplicadaError(ExcepcionValidacionDominio):
    def __init__(self):
        super().__init__(
            "Ya existe una conexión registrada entre estos dos nodos en este sistema experto.",
            {"conexion": ["No se permiten conexiones duplicadas en la misma dirección."]},
        )


class NodosDistintoSistemaError(ExcepcionValidacionDominio):
    def __init__(self):
        super().__init__(
            "Ambos nodos deben pertenecer al mismo sistema experto.",
            {
                "sistema_experto": [
                    "Los nodos seleccionados pertenecen a sistemas expertos diferentes."
                ]
            },
        )


class ReferenciaInvalidaError(ExcepcionValidacionDominio):
    def __init__(self, tipo: str, referencia_id):
        super().__init__(
            f"El elemento referenciado de tipo '{tipo}' con ID {referencia_id} no existe.",
            {
                "referencia_id": [
                    f"No existe el objeto de tipo {tipo} con el identificador proporcionado."
                ]
            },
        )
