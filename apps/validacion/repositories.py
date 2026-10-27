"""
Repositorios para el módulo de Validación de Bases de Conocimiento.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from apps.validacion.entities import IncidenciaValidacion, ResultadoValidacion
from apps.validacion.models import IncidenciaValidacionModel, ValidacionBaseModel


class ValidacionBaseRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_validacion: UUID) -> Optional[ResultadoValidacion]:
        pass

    @abstractmethod
    def obtener_ultima_por_base(self, id_base: UUID) -> Optional[ResultadoValidacion]:
        pass

    @abstractmethod
    def listar_incidencias(
        self,
        id_validacion: UUID,
        severidad: Optional[str] = None,
        tipo: Optional[str] = None,
    ) -> List[IncidenciaValidacion]:
        pass

    @abstractmethod
    def guardar(self, resultado: ResultadoValidacion) -> ResultadoValidacion:
        pass


class DjangoValidacionBaseRepositorio(ValidacionBaseRepositorio):

    @staticmethod
    def _incidencia_a_entidad(m: IncidenciaValidacionModel) -> IncidenciaValidacion:
        return IncidenciaValidacion(
            id=m.id,
            validacion_id=m.validacion_id,
            codigo=m.codigo,
            tipo=m.tipo,
            severidad=m.severidad,
            entidad_tipo=m.entidad_tipo,
            entidad_id=m.entidad_id,
            entidad_nombre=m.entidad_nombre,
            descripcion=m.descripcion,
            posible_causa=m.posible_causa,
            sugerencia=m.sugerencia,
            creada_en=m.creada_en,
        )

    def _validacion_a_entidad(
        self, m: ValidacionBaseModel, incluir_incidencias: bool = True
    ) -> ResultadoValidacion:
        incidencias = []
        if incluir_incidencias:
            incidencias = [
                self._incidencia_a_entidad(inc)
                for inc in m.incidencias.all().order_by("severidad", "codigo")
            ]
        return ResultadoValidacion(
            id=m.id,
            base_conocimiento_id=m.base_conocimiento_id,
            fecha_validacion=m.fecha_validacion,
            es_valida=m.es_valida,
            total_errores=m.total_errores,
            total_advertencias=m.total_advertencias,
            resumen=m.resumen or "",
            incidencias=incidencias,
        )

    def obtener_por_id(self, id_validacion: UUID) -> Optional[ResultadoValidacion]:
        try:
            m = ValidacionBaseModel.objects.prefetch_related("incidencias").get(
                id=id_validacion
            )
            return self._validacion_a_entidad(m)
        except ValidacionBaseModel.DoesNotExist:
            return None

    def obtener_ultima_por_base(self, id_base: UUID) -> Optional[ResultadoValidacion]:
        m = (
            ValidacionBaseModel.objects.filter(base_conocimiento_id=id_base)
            .prefetch_related("incidencias")
            .order_by("-fecha_validacion")
            .first()
        )
        return self._validacion_a_entidad(m) if m else None

    def listar_incidencias(
        self,
        id_validacion: UUID,
        severidad: Optional[str] = None,
        tipo: Optional[str] = None,
    ) -> List[IncidenciaValidacion]:
        qs = IncidenciaValidacionModel.objects.filter(validacion_id=id_validacion)
        if severidad:
            qs = qs.filter(severidad=severidad.upper())
        if tipo:
            qs = qs.filter(tipo=tipo.upper())
        return [self._incidencia_a_entidad(m) for m in qs.order_by("severidad", "codigo")]

    def guardar(self, resultado: ResultadoValidacion) -> ResultadoValidacion:
        m, _ = ValidacionBaseModel.objects.update_or_create(
            id=resultado.id,
            defaults={
                "base_conocimiento_id": resultado.base_conocimiento_id,
                "es_valida": resultado.es_valida,
                "total_errores": resultado.total_errores,
                "total_advertencias": resultado.total_advertencias,
                "resumen": resultado.resumen,
            },
        )
        # Guardar incidencias
        inc_modelos = [
            IncidenciaValidacionModel(
                id=inc.id,
                validacion_id=m.id,
                codigo=inc.codigo,
                tipo=inc.tipo,
                severidad=inc.severidad,
                entidad_tipo=inc.entidad_tipo,
                entidad_id=inc.entidad_id,
                entidad_nombre=inc.entidad_nombre,
                descripcion=inc.descripcion,
                posible_causa=inc.posible_causa,
                sugerencia=inc.sugerencia,
            )
            for inc in resultado.incidencias
        ]
        IncidenciaValidacionModel.objects.bulk_create(inc_modelos, ignore_conflicts=True)
        return self._validacion_a_entidad(m)
