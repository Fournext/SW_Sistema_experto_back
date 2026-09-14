"""
Repositorios para el módulo de Inferencia.
Incluye interfaces abstractas y adaptadores concretos con Django ORM.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from apps.inferencia.entities import DetalleInferencia, EjecucionInferencia
from apps.inferencia.models import DetalleInferenciaModel, EjecucionInferenciaModel
from compartido.constantes.enums import EstadoEjecucion, EstadoReglaInferencia


class EjecucionInferenciaRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_ejecucion: UUID) -> Optional[EjecucionInferencia]:
        pass

    @abstractmethod
    def listar_por_sistema(self, id_sistema: UUID) -> List[EjecucionInferencia]:
        pass

    @abstractmethod
    def guardar(self, ejecucion: EjecucionInferencia) -> EjecucionInferencia:
        pass


class DetalleInferenciaRepositorio(ABC):
    @abstractmethod
    def listar_por_ejecucion(self, id_ejecucion: UUID) -> List[DetalleInferencia]:
        pass

    @abstractmethod
    def guardar(self, detalle: DetalleInferencia) -> DetalleInferencia:
        pass

    @abstractmethod
    def guardar_lote(self, detalles: List[DetalleInferencia]) -> List[DetalleInferencia]:
        pass


class DjangoEjecucionInferenciaRepositorio(EjecucionInferenciaRepositorio):

    @staticmethod
    def _a_entidad(m: EjecucionInferenciaModel) -> EjecucionInferencia:
        return EjecucionInferencia(
            id=m.id,
            sistema_experto_id=m.sistema_experto_id,
            estado=EstadoEjecucion(m.estado),
            fecha_inicio=m.fecha_inicio,
            fecha_fin=m.fecha_fin,
            conclusion_final=m.conclusion_final,
        )

    def obtener_por_id(self, id_ejecucion: UUID) -> Optional[EjecucionInferencia]:
        try:
            return self._a_entidad(EjecucionInferenciaModel.objects.get(id=id_ejecucion))
        except EjecucionInferenciaModel.DoesNotExist:
            return None

    def listar_por_sistema(self, id_sistema: UUID) -> List[EjecucionInferencia]:
        return [
            self._a_entidad(m)
            for m in EjecucionInferenciaModel.objects.filter(
                sistema_experto_id=id_sistema
            ).order_by("-fecha_inicio")
        ]

    def guardar(self, ejecucion: EjecucionInferencia) -> EjecucionInferencia:
        m, _ = EjecucionInferenciaModel.objects.update_or_create(
            id=ejecucion.id,
            defaults={
                "sistema_experto_id": ejecucion.sistema_experto_id,
                "estado": (
                    ejecucion.estado.value
                    if hasattr(ejecucion.estado, "value")
                    else ejecucion.estado
                ),
                "fecha_fin": ejecucion.fecha_fin,
                "conclusion_final": ejecucion.conclusion_final,
            },
        )
        return self._a_entidad(m)


class DjangoDetalleInferenciaRepositorio(DetalleInferenciaRepositorio):

    @staticmethod
    def _a_entidad(m: DetalleInferenciaModel) -> DetalleInferencia:
        return DetalleInferencia(
            id=m.id,
            ejecucion_id=m.ejecucion_id,
            regla_id=m.regla_id,
            orden=m.orden,
            estado_regla=EstadoReglaInferencia(m.estado_regla),
            condiciones_cumplidas=m.condiciones_cumplidas,
            resultado_generado=m.resultado_generado,
        )

    def listar_por_ejecucion(self, id_ejecucion: UUID) -> List[DetalleInferencia]:
        modelos = DetalleInferenciaModel.objects.filter(
            ejecucion_id=id_ejecucion
        ).order_by("orden")
        return [self._a_entidad(m) for m in modelos]

    def guardar(self, detalle: DetalleInferencia) -> DetalleInferencia:
        estado_val = (
            detalle.estado_regla.value
            if hasattr(detalle.estado_regla, "value")
            else detalle.estado_regla
        )
        m, _ = DetalleInferenciaModel.objects.update_or_create(
            id=detalle.id,
            defaults={
                "ejecucion_id": detalle.ejecucion_id,
                "regla_id": detalle.regla_id,
                "orden": detalle.orden,
                "estado_regla": estado_val,
                "condiciones_cumplidas": detalle.condiciones_cumplidas,
                "resultado_generado": detalle.resultado_generado,
            },
        )
        return self._a_entidad(m)

    def guardar_lote(self, detalles: List[DetalleInferencia]) -> List[DetalleInferencia]:
        modelos = [
            DetalleInferenciaModel(
                id=d.id,
                ejecucion_id=d.ejecucion_id,
                regla_id=d.regla_id,
                orden=d.orden,
                estado_regla=(
                    d.estado_regla.value
                    if hasattr(d.estado_regla, "value")
                    else d.estado_regla
                ),
                condiciones_cumplidas=d.condiciones_cumplidas,
                resultado_generado=d.resultado_generado,
            )
            for d in detalles
        ]
        DetalleInferenciaModel.objects.bulk_create(modelos)
        return detalles
