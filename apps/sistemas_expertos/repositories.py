"""
Repositorios para el módulo de Sistemas Expertos.
Incluye la interfaz abstracta y la implementación concreta con Django ORM.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from apps.sistemas_expertos.entities import SistemaExperto
from apps.sistemas_expertos.models import SistemaExpertoModel
from compartido.constantes.enums import EstadoSistema


class SistemaExpertoRepositorio(ABC):
    """Interfaz abstracta para el repositorio de Sistemas Expertos."""

    @abstractmethod
    def obtener_por_id(self, id_sistema: UUID) -> Optional[SistemaExperto]:
        pass

    @abstractmethod
    def listar(self) -> List[SistemaExperto]:
        pass

    @abstractmethod
    def guardar(self, sistema: SistemaExperto) -> SistemaExperto:
        pass

    @abstractmethod
    def eliminar(self, id_sistema: UUID) -> bool:
        pass

    @abstractmethod
    def existe_por_id(self, id_sistema: UUID) -> bool:
        pass


class DjangoSistemaExpertoRepositorio(SistemaExpertoRepositorio):
    """Adaptador de persistencia de Sistemas Expertos con Django ORM."""

    @staticmethod
    def _a_entidad(modelo: SistemaExpertoModel) -> SistemaExperto:
        return SistemaExperto(
            id=modelo.id,
            nombre=modelo.nombre,
            descripcion=modelo.descripcion,
            estado=EstadoSistema(modelo.estado),
            creado_en=modelo.creado_en,
            actualizado_en=modelo.actualizado_en,
        )

    def obtener_por_id(self, id_sistema: UUID) -> Optional[SistemaExperto]:
        try:
            modelo = SistemaExpertoModel.objects.get(id=id_sistema)
            return self._a_entidad(modelo)
        except SistemaExpertoModel.DoesNotExist:
            return None

    def listar(self) -> List[SistemaExperto]:
        modelos = SistemaExpertoModel.objects.all().order_by("-creado_en")
        return [self._a_entidad(m) for m in modelos]

    def guardar(self, sistema: SistemaExperto) -> SistemaExperto:
        modelo, _ = SistemaExpertoModel.objects.update_or_create(
            id=sistema.id,
            defaults={
                "nombre": sistema.nombre,
                "descripcion": sistema.descripcion,
                "estado": sistema.estado.value if hasattr(sistema.estado, "value") else sistema.estado,
            },
        )
        return self._a_entidad(modelo)

    def eliminar(self, id_sistema: UUID) -> bool:
        filas_borradas, _ = SistemaExpertoModel.objects.filter(id=id_sistema).delete()
        return filas_borradas > 0

    def existe_por_id(self, id_sistema: UUID) -> bool:
        return SistemaExpertoModel.objects.filter(id=id_sistema).exists()
