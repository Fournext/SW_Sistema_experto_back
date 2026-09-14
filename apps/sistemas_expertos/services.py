"""
Servicios y casos de uso para el módulo de Sistemas Expertos.
Orquestan la lógica de negocio y la persistencia.
"""
from typing import List, Optional
from uuid import UUID

from apps.sistemas_expertos.entities import SistemaExperto
from apps.sistemas_expertos.exceptions import SistemaExpertoNoEncontrado
from apps.sistemas_expertos.repositories import (
    DjangoSistemaExpertoRepositorio,
    SistemaExpertoRepositorio,
)
from apps.sistemas_expertos.validators import ValidadorSistemaExperto
from apps.base_conocimiento.models import BaseConocimientoModel
from compartido.constantes.enums import EstadoSistema


class ServicioDominioSistemaExperto:
    """Lógica de dominio transversal para sistemas expertos."""

    @staticmethod
    def validar_y_preparar(sistema: SistemaExperto) -> None:
        ValidadorSistemaExperto.validar_nombre(sistema.nombre)
        sistema.nombre = sistema.nombre.strip()


class CrearSistemaExperto:
    """Caso de uso: Crear un nuevo Sistema Experto y su Base de Conocimiento asociada."""

    def __init__(self, repositorio: Optional[SistemaExpertoRepositorio] = None):
        self.repositorio = repositorio or DjangoSistemaExpertoRepositorio()

    def ejecutar(
        self,
        nombre: str,
        descripcion: Optional[str] = None,
        estado: str = EstadoSistema.BORRADOR.value,
    ) -> SistemaExperto:
        nuevo_sistema = SistemaExperto(
            nombre=nombre,
            descripcion=descripcion,
            estado=EstadoSistema(estado),
        )
        ServicioDominioSistemaExperto.validar_y_preparar(nuevo_sistema)
        sistema_guardado = self.repositorio.guardar(nuevo_sistema)

        # Crear automáticamente la Base de Conocimiento asociada (1:1)
        BaseConocimientoModel.objects.get_or_create(
            sistema_experto_id=sistema_guardado.id,
            defaults={"nombre": f"BC - {sistema_guardado.nombre}", "version": 1},
        )
        return sistema_guardado


class ActualizarSistemaExperto:
    """Caso de uso: Actualizar total o parcialmente un Sistema Experto."""

    def __init__(self, repositorio: Optional[SistemaExpertoRepositorio] = None):
        self.repositorio = repositorio or DjangoSistemaExpertoRepositorio()

    def ejecutar(
        self,
        id_sistema: UUID,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        estado: Optional[str] = None,
    ) -> SistemaExperto:
        sistema = self.repositorio.obtener_por_id(id_sistema)
        if not sistema:
            raise SistemaExpertoNoEncontrado(id_sistema)

        if nombre is not None:
            sistema.nombre = nombre
            ServicioDominioSistemaExperto.validar_y_preparar(sistema)

        if descripcion is not None:
            sistema.descripcion = descripcion

        if estado is not None:
            sistema.estado = EstadoSistema(estado)

        return self.repositorio.guardar(sistema)


class ObtenerSistemaExperto:
    """Caso de uso: Obtener un Sistema Experto por su ID."""

    def __init__(self, repositorio: Optional[SistemaExpertoRepositorio] = None):
        self.repositorio = repositorio or DjangoSistemaExpertoRepositorio()

    def ejecutar(self, id_sistema: UUID) -> SistemaExperto:
        sistema = self.repositorio.obtener_por_id(id_sistema)
        if not sistema:
            raise SistemaExpertoNoEncontrado(id_sistema)
        return sistema


class ListarSistemasExpertos:
    """Caso de uso: Listar todos los Sistemas Expertos."""

    def __init__(self, repositorio: Optional[SistemaExpertoRepositorio] = None):
        self.repositorio = repositorio or DjangoSistemaExpertoRepositorio()

    def ejecutar(self) -> List[SistemaExperto]:
        return self.repositorio.listar()


class EliminarSistemaExperto:
    """Caso de uso: Eliminar un Sistema Experto por su ID."""

    def __init__(self, repositorio: Optional[SistemaExpertoRepositorio] = None):
        self.repositorio = repositorio or DjangoSistemaExpertoRepositorio()

    def ejecutar(self, id_sistema: UUID) -> None:
        if not self.repositorio.existe_por_id(id_sistema):
            raise SistemaExpertoNoEncontrado(id_sistema)
        self.repositorio.eliminar(id_sistema)


class SistemaExpertoServicio:
    """Fachada de servicios para el módulo de Sistemas Expertos."""

    crear = CrearSistemaExperto
    actualizar = ActualizarSistemaExperto
    obtener = ObtenerSistemaExperto
    listar = ListarSistemasExpertos
    eliminar = EliminarSistemaExperto
