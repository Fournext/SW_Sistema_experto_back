"""
Validadores de dominio para el Editor Visual.
"""
from uuid import UUID
from apps.editor_visual.entities import NodoVisual
from apps.editor_visual.exceptions import (
    ConexionConsigoMismoError,
    NodosDistintoSistemaError,
)


class ValidadorEditorVisual:
    """Valida reglas estructurales y de consistencia del lienzo visual."""

    @staticmethod
    def validar_conexion(
        id_origen: UUID,
        id_destino: UUID,
        nodo_origen: NodoVisual,
        nodo_destino: NodoVisual,
    ) -> None:
        if id_origen == id_destino:
            raise ConexionConsigoMismoError()

        if nodo_origen.sistema_experto_id != nodo_destino.sistema_experto_id:
            raise NodosDistintoSistemaError()
