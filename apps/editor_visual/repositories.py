"""
Repositorios para el módulo de Editor Visual.
Incluye interfaces abstractas y adaptadores concretos con Django ORM.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from apps.editor_visual.entities import ConexionVisual, NodoVisual
from apps.editor_visual.models import ConexionVisualModel, NodoVisualModel
from compartido.constantes.enums import TipoNodoVisual


class NodoVisualRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_nodo: UUID) -> Optional[NodoVisual]:
        pass

    @abstractmethod
    def listar_por_sistema(self, id_sistema: UUID) -> List[NodoVisual]:
        pass

    @abstractmethod
    def guardar(self, nodo: NodoVisual) -> NodoVisual:
        pass

    @abstractmethod
    def eliminar(self, id_nodo: UUID) -> bool:
        pass


class ConexionVisualRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_conexion: UUID) -> Optional[ConexionVisual]:
        pass

    @abstractmethod
    def listar_por_sistema(self, id_sistema: UUID) -> List[ConexionVisual]:
        pass

    @abstractmethod
    def existe_conexion(self, id_sistema: UUID, id_origen: UUID, id_destino: UUID) -> bool:
        pass

    @abstractmethod
    def guardar(self, conexion: ConexionVisual) -> ConexionVisual:
        pass

    @abstractmethod
    def eliminar(self, id_conexion: UUID) -> bool:
        pass


class DjangoNodoVisualRepositorio(NodoVisualRepositorio):

    @staticmethod
    def _a_entidad(m: NodoVisualModel) -> NodoVisual:
        return NodoVisual(
            id=m.id,
            sistema_experto_id=m.sistema_experto_id,
            tipo=TipoNodoVisual(m.tipo),
            referencia_id=m.referencia_id,
            posicion_x=m.posicion_x,
            posicion_y=m.posicion_y,
        )

    def obtener_por_id(self, id_nodo: UUID) -> Optional[NodoVisual]:
        try:
            return self._a_entidad(NodoVisualModel.objects.get(id=id_nodo))
        except NodoVisualModel.DoesNotExist:
            return None

    def listar_por_sistema(self, id_sistema: UUID) -> List[NodoVisual]:
        return [
            self._a_entidad(m)
            for m in NodoVisualModel.objects.filter(sistema_experto_id=id_sistema)
        ]

    def guardar(self, nodo: NodoVisual) -> NodoVisual:
        m, _ = NodoVisualModel.objects.update_or_create(
            id=nodo.id,
            defaults={
                "sistema_experto_id": nodo.sistema_experto_id,
                "tipo": nodo.tipo.value if hasattr(nodo.tipo, "value") else nodo.tipo,
                "referencia_id": nodo.referencia_id,
                "posicion_x": nodo.posicion_x,
                "posicion_y": nodo.posicion_y,
            },
        )
        return self._a_entidad(m)

    def eliminar(self, id_nodo: UUID) -> bool:
        filas, _ = NodoVisualModel.objects.filter(id=id_nodo).delete()
        return filas > 0


class DjangoConexionVisualRepositorio(ConexionVisualRepositorio):

    @staticmethod
    def _a_entidad(m: ConexionVisualModel) -> ConexionVisual:
        return ConexionVisual(
            id=m.id,
            sistema_experto_id=m.sistema_experto_id,
            nodo_origen_id=m.nodo_origen_id,
            nodo_destino_id=m.nodo_destino_id,
            etiqueta=m.etiqueta,
            tipo=m.tipo,
        )

    def obtener_por_id(self, id_conexion: UUID) -> Optional[ConexionVisual]:
        try:
            return self._a_entidad(ConexionVisualModel.objects.get(id=id_conexion))
        except ConexionVisualModel.DoesNotExist:
            return None

    def listar_por_sistema(self, id_sistema: UUID) -> List[ConexionVisual]:
        return [
            self._a_entidad(m)
            for m in ConexionVisualModel.objects.filter(sistema_experto_id=id_sistema)
        ]

    def existe_conexion(self, id_sistema: UUID, id_origen: UUID, id_destino: UUID) -> bool:
        return ConexionVisualModel.objects.filter(
            sistema_experto_id=id_sistema,
            nodo_origen_id=id_origen,
            nodo_destino_id=id_destino,
        ).exists()

    def guardar(self, conexion: ConexionVisual) -> ConexionVisual:
        m, _ = ConexionVisualModel.objects.update_or_create(
            id=conexion.id,
            defaults={
                "sistema_experto_id": conexion.sistema_experto_id,
                "nodo_origen_id": conexion.nodo_origen_id,
                "nodo_destino_id": conexion.nodo_destino_id,
                "etiqueta": conexion.etiqueta,
                "tipo": conexion.tipo,
            },
        )
        return self._a_entidad(m)

    def eliminar(self, id_conexion: UUID) -> bool:
        filas, _ = ConexionVisualModel.objects.filter(id=id_conexion).delete()
        return filas > 0
