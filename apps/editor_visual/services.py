"""
Servicios y casos de uso para el módulo de Editor Visual.
"""
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from apps.base_conocimiento.models import (
    ConclusionModel,
    CondicionModel,
    HechoModel,
    ReglaModel,
    VariableModel,
)
from apps.editor_visual.entities import ConexionVisual, NodoVisual
from apps.editor_visual.exceptions import (
    ConexionDuplicadaError,
    ConexionVisualNoEncontrada,
    NodoVisualNoEncontrado,
    ReferenciaInvalidaError,
)
from apps.editor_visual.repositories import (
    ConexionVisualRepositorio,
    DjangoConexionVisualRepositorio,
    DjangoNodoVisualRepositorio,
    NodoVisualRepositorio,
)
from apps.editor_visual.validators import ValidadorEditorVisual
from apps.sistemas_expertos.exceptions import SistemaExpertoNoEncontrado
from apps.sistemas_expertos.repositories import (
    DjangoSistemaExpertoRepositorio,
    SistemaExpertoRepositorio,
)
from compartido.constantes.enums import TipoNodoVisual


class CrearNodoVisual:
    def __init__(
        self,
        repo_nodo: Optional[NodoVisualRepositorio] = None,
        repo_se: Optional[SistemaExpertoRepositorio] = None,
    ):
        self.repo_nodo = repo_nodo or DjangoNodoVisualRepositorio()
        self.repo_se = repo_se or DjangoSistemaExpertoRepositorio()

    def _validar_existencia_referencia(self, tipo: TipoNodoVisual, ref_id: UUID) -> None:
        """Verifica que el elemento de dominio referenciado exista realmente."""
        existe = False
        if tipo == TipoNodoVisual.HECHO:
            existe = HechoModel.objects.filter(id=ref_id).exists()
        elif tipo == TipoNodoVisual.VARIABLE:
            existe = VariableModel.objects.filter(id=ref_id).exists()
        elif tipo == TipoNodoVisual.CONDICION:
            existe = CondicionModel.objects.filter(id=ref_id).exists()
        elif tipo == TipoNodoVisual.REGLA:
            existe = ReglaModel.objects.filter(id=ref_id).exists()
        elif tipo == TipoNodoVisual.CONCLUSION:
            existe = ConclusionModel.objects.filter(id=ref_id).exists()

        if not existe:
            raise ReferenciaInvalidaError(tipo=tipo.value, referencia_id=ref_id)

    def ejecutar(
        self,
        sistema_experto_id: UUID,
        tipo: str,
        referencia_id: UUID,
        posicion_x: Decimal = Decimal("0.0"),
        posicion_y: Decimal = Decimal("0.0"),
    ) -> NodoVisual:
        if not self.repo_se.existe_por_id(sistema_experto_id):
            raise SistemaExpertoNoEncontrado(sistema_experto_id)

        tipo_enum = TipoNodoVisual(tipo)
        self._validar_existencia_referencia(tipo_enum, referencia_id)

        nodo = NodoVisual(
            sistema_experto_id=sistema_experto_id,
            tipo=tipo_enum,
            referencia_id=referencia_id,
            posicion_x=posicion_x,
            posicion_y=posicion_y,
        )
        return self.repo_nodo.guardar(nodo)


class MoverNodoVisual:
    def __init__(self, repo_nodo: Optional[NodoVisualRepositorio] = None):
        self.repo_nodo = repo_nodo or DjangoNodoVisualRepositorio()

    def ejecutar(
        self,
        id_nodo: UUID,
        posicion_x: Decimal,
        posicion_y: Decimal,
    ) -> NodoVisual:
        nodo = self.repo_nodo.obtener_por_id(id_nodo)
        if not nodo:
            raise NodoVisualNoEncontrado(id_nodo)

        nodo.posicion_x = posicion_x
        nodo.posicion_y = posicion_y
        return self.repo_nodo.guardar(nodo)


class EliminarNodoVisual:
    def __init__(self, repo_nodo: Optional[NodoVisualRepositorio] = None):
        self.repo_nodo = repo_nodo or DjangoNodoVisualRepositorio()

    def ejecutar(self, id_nodo: UUID) -> None:
        nodo = self.repo_nodo.obtener_por_id(id_nodo)
        if not nodo:
            raise NodoVisualNoEncontrado(id_nodo)
        self.repo_nodo.eliminar(id_nodo)


class CrearConexionVisual:
    def __init__(
        self,
        repo_conexion: Optional[ConexionVisualRepositorio] = None,
        repo_nodo: Optional[NodoVisualRepositorio] = None,
    ):
        self.repo_conexion = repo_conexion or DjangoConexionVisualRepositorio()
        self.repo_nodo = repo_nodo or DjangoNodoVisualRepositorio()

    def ejecutar(
        self,
        sistema_experto_id: UUID,
        nodo_origen_id: UUID,
        nodo_destino_id: UUID,
        etiqueta: Optional[str] = None,
        tipo: Optional[str] = None,
    ) -> ConexionVisual:
        nodo_origen = self.repo_nodo.obtener_por_id(nodo_origen_id)
        if not nodo_origen:
            raise NodoVisualNoEncontrado(nodo_origen_id)

        nodo_destino = self.repo_nodo.obtener_por_id(nodo_destino_id)
        if not nodo_destino:
            raise NodoVisualNoEncontrado(nodo_destino_id)

        ValidadorEditorVisual.validar_conexion(
            id_origen=nodo_origen_id,
            id_destino=nodo_destino_id,
            nodo_origen=nodo_origen,
            nodo_destino=nodo_destino,
        )

        if self.repo_conexion.existe_conexion(
            sistema_experto_id, nodo_origen_id, nodo_destino_id
        ):
            raise ConexionDuplicadaError()

        conexion = ConexionVisual(
            sistema_experto_id=sistema_experto_id,
            nodo_origen_id=nodo_origen_id,
            nodo_destino_id=nodo_destino_id,
            etiqueta=etiqueta,
            tipo=tipo,
        )
        return self.repo_conexion.guardar(conexion)


class EliminarConexionVisual:
    def __init__(self, repo_conexion: Optional[ConexionVisualRepositorio] = None):
        self.repo_conexion = repo_conexion or DjangoConexionVisualRepositorio()

    def ejecutar(self, id_conexion: UUID) -> None:
        conexion = self.repo_conexion.obtener_por_id(id_conexion)
        if not conexion:
            raise ConexionVisualNoEncontrada(id_conexion)
        self.repo_conexion.eliminar(id_conexion)


class ObtenerEditorVisual:
    def __init__(
        self,
        repo_nodo: Optional[NodoVisualRepositorio] = None,
        repo_conexion: Optional[ConexionVisualRepositorio] = None,
        repo_se: Optional[SistemaExpertoRepositorio] = None,
    ):
        self.repo_nodo = repo_nodo or DjangoNodoVisualRepositorio()
        self.repo_conexion = repo_conexion or DjangoConexionVisualRepositorio()
        self.repo_se = repo_se or DjangoSistemaExpertoRepositorio()

    def ejecutar(self, sistema_experto_id: UUID) -> Dict[str, List]:
        if not self.repo_se.existe_por_id(sistema_experto_id):
            raise SistemaExpertoNoEncontrado(sistema_experto_id)

        nodos = self.repo_nodo.listar_por_sistema(sistema_experto_id)
        conexiones = self.repo_conexion.listar_por_sistema(sistema_experto_id)
        return {
            "sistema_experto_id": sistema_experto_id,
            "nodos": nodos,
            "conexiones": conexiones,
        }
