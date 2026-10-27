"""
Repositorios para el módulo de Actividades Educativas (Sprint 2 - HU-23, HU-24, HU-25).
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from django.db import transaction

from apps.actividades.entities import (
    ActividadEducativa,
    AsignacionActividad,
    Curso,
    EntregaActividad,
)
from apps.actividades.models import (
    ActividadEducativaModel,
    AsignacionActividadModel,
    CursoModel,
    EntregaActividadModel,
)


class CursoRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_curso: UUID) -> Optional[Curso]:
        pass

    @abstractmethod
    def listar(self, docente_id: Optional[int] = None, solo_activos: bool = True) -> List[Curso]:
        pass

    @abstractmethod
    def guardar(self, curso: Curso) -> Curso:
        pass


class DjangoCursoRepositorio(CursoRepositorio):
    @staticmethod
    def _a_entidad(m: CursoModel) -> Curso:
        return Curso(
            id=m.id,
            codigo=m.codigo,
            nombre=m.nombre,
            descripcion=m.descripcion,
            docente_id=m.docente_id,
            activo=m.activo,
            creado_en=m.creado_en,
        )

    def obtener_por_id(self, id_curso: UUID) -> Optional[Curso]:
        try:
            m = CursoModel.objects.get(id=id_curso)
            return self._a_entidad(m)
        except CursoModel.DoesNotExist:
            return None

    def listar(self, docente_id: Optional[int] = None, solo_activos: bool = True) -> List[Curso]:
        qs = CursoModel.objects.all()
        if solo_activos:
            qs = qs.filter(activo=True)
        if docente_id is not None:
            qs = qs.filter(docente_id=docente_id)
        return [self._a_entidad(m) for m in qs.order_by("nombre")]

    def guardar(self, curso: Curso) -> Curso:
        m, _ = CursoModel.objects.update_or_create(
            id=curso.id,
            defaults={
                "codigo": curso.codigo,
                "nombre": curso.nombre,
                "descripcion": curso.descripcion,
                "docente_id": curso.docente_id,
                "activo": curso.activo,
            },
        )
        return self._a_entidad(m)


class ActividadEducativaRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_actividad: UUID) -> Optional[ActividadEducativa]:
        pass

    @abstractmethod
    def listar(
        self,
        docente_id: Optional[int] = None,
        estado: Optional[str] = None,
        solo_activas: bool = True,
    ) -> List[ActividadEducativa]:
        pass

    @abstractmethod
    def guardar(self, actividad: ActividadEducativa) -> ActividadEducativa:
        pass

    @abstractmethod
    def desactivar(self, id_actividad: UUID) -> bool:
        pass


class DjangoActividadEducativaRepositorio(ActividadEducativaRepositorio):
    @staticmethod
    def _a_entidad(m: ActividadEducativaModel) -> ActividadEducativa:
        return ActividadEducativa(
            id=m.id,
            docente_id=m.docente_id,
            docente_username=m.docente.username if m.docente else None,
            sistema_experto_id=m.sistema_experto_id,
            sistema_experto_nombre=m.sistema_experto.nombre if m.sistema_experto else None,
            titulo=m.titulo,
            instrucciones=m.instrucciones,
            dificultad=m.dificultad,
            estado=m.estado,
            activa=m.activa,
            creada_en=m.creada_en,
            actualizada_en=m.actualizada_en,
        )

    def obtener_por_id(self, id_actividad: UUID) -> Optional[ActividadEducativa]:
        try:
            m = (
                ActividadEducativaModel.objects.select_related("docente", "sistema_experto")
                .get(id=id_actividad)
            )
            return self._a_entidad(m)
        except ActividadEducativaModel.DoesNotExist:
            return None

    def listar(
        self,
        docente_id: Optional[int] = None,
        estado: Optional[str] = None,
        solo_activas: bool = True,
    ) -> List[ActividadEducativa]:
        qs = ActividadEducativaModel.objects.select_related("docente", "sistema_experto")
        if solo_activas:
            qs = qs.filter(activa=True)
        if docente_id is not None:
            qs = qs.filter(docente_id=docente_id)
        if estado:
            qs = qs.filter(estado=estado.upper())
        return [self._a_entidad(m) for m in qs.order_by("-creada_en")]

    def guardar(self, actividad: ActividadEducativa) -> ActividadEducativa:
        m, _ = ActividadEducativaModel.objects.update_or_create(
            id=actividad.id,
            defaults={
                "docente_id": actividad.docente_id,
                "sistema_experto_id": actividad.sistema_experto_id,
                "titulo": actividad.titulo,
                "instrucciones": actividad.instrucciones,
                "dificultad": actividad.dificultad,
                "estado": actividad.estado,
                "activa": actividad.activa,
            },
        )
        return self._a_entidad(m)

    def desactivar(self, id_actividad: UUID) -> bool:
        filas = ActividadEducativaModel.objects.filter(id=id_actividad).update(activa=False)
        return filas > 0


class AsignacionActividadRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_asignacion: UUID) -> Optional[AsignacionActividad]:
        pass

    @abstractmethod
    def obtener_por_actividad_y_curso(
        self, id_actividad: UUID, id_curso: UUID
    ) -> Optional[AsignacionActividad]:
        pass

    @abstractmethod
    def listar(
        self,
        curso_id: Optional[UUID] = None,
        actividad_id: Optional[UUID] = None,
        estado: Optional[str] = None,
    ) -> List[AsignacionActividad]:
        pass

    @abstractmethod
    def guardar(self, asignacion: AsignacionActividad) -> AsignacionActividad:
        pass


class DjangoAsignacionActividadRepositorio(AsignacionActividadRepositorio):
    @staticmethod
    def _a_entidad(m: AsignacionActividadModel) -> AsignacionActividad:
        return AsignacionActividad(
            id=m.id,
            actividad_id=m.actividad_id,
            actividad_titulo=m.actividad.titulo if m.actividad else None,
            curso_id=m.curso_id,
            curso_codigo=m.curso.codigo if m.curso else None,
            curso_nombre=m.curso.nombre if m.curso else None,
            fecha_asignacion=m.fecha_asignacion,
            fecha_limite=m.fecha_limite,
            estado=m.estado,
        )

    def obtener_por_id(self, id_asignacion: UUID) -> Optional[AsignacionActividad]:
        try:
            m = AsignacionActividadModel.objects.select_related("actividad", "curso").get(
                id=id_asignacion
            )
            return self._a_entidad(m)
        except AsignacionActividadModel.DoesNotExist:
            return None

    def obtener_por_actividad_y_curso(
        self, id_actividad: UUID, id_curso: UUID
    ) -> Optional[AsignacionActividad]:
        m = (
            AsignacionActividadModel.objects.select_related("actividad", "curso")
            .filter(actividad_id=id_actividad, curso_id=id_curso)
            .first()
        )
        return self._a_entidad(m) if m else None

    def listar(
        self,
        curso_id: Optional[UUID] = None,
        actividad_id: Optional[UUID] = None,
        estado: Optional[str] = None,
    ) -> List[AsignacionActividad]:
        qs = AsignacionActividadModel.objects.select_related("actividad", "curso")
        if curso_id:
            qs = qs.filter(curso_id=curso_id)
        if actividad_id:
            qs = qs.filter(actividad_id=actividad_id)
        if estado:
            qs = qs.filter(estado=estado.upper())
        return [self._a_entidad(m) for m in qs.order_by("-fecha_asignacion")]

    def guardar(self, asignacion: AsignacionActividad) -> AsignacionActividad:
        m, _ = AsignacionActividadModel.objects.update_or_create(
            id=asignacion.id,
            defaults={
                "actividad_id": asignacion.actividad_id,
                "curso_id": asignacion.curso_id,
                "fecha_limite": asignacion.fecha_limite,
                "estado": asignacion.estado,
            },
        )
        return self._a_entidad(m)


class EntregaActividadRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_entrega: UUID) -> Optional[EntregaActividad]:
        pass

    @abstractmethod
    def obtener_por_asignacion_y_estudiante(
        self, id_asignacion: UUID, id_estudiante: int
    ) -> Optional[EntregaActividad]:
        pass

    @abstractmethod
    def listar_por_asignacion(self, id_asignacion: UUID) -> List[EntregaActividad]:
        pass

    @abstractmethod
    def listar_por_estudiante(self, id_estudiante: int) -> List[EntregaActividad]:
        pass

    @abstractmethod
    def guardar(self, entrega: EntregaActividad) -> EntregaActividad:
        pass


class DjangoEntregaActividadRepositorio(EntregaActividadRepositorio):
    @staticmethod
    def _a_entidad(m: EntregaActividadModel) -> EntregaActividad:
        return EntregaActividad(
            id=m.id,
            asignacion_id=m.asignacion_id,
            estudiante_id=m.estudiante_id,
            estudiante_username=m.estudiante.username if m.estudiante else None,
            estado=m.estado,
            solucion_texto=m.solucion_texto,
            hechos_ingresados=m.hechos_ingresados or [],
            ejecucion_inferencia_id=m.ejecucion_inferencia_id,
            fecha_envio=m.fecha_envio,
            creada_en=m.creada_en,
            actualizada_en=m.actualizada_en,
        )

    def obtener_por_id(self, id_entrega: UUID) -> Optional[EntregaActividad]:
        try:
            m = EntregaActividadModel.objects.select_related("estudiante", "asignacion").get(
                id=id_entrega
            )
            return self._a_entidad(m)
        except EntregaActividadModel.DoesNotExist:
            return None

    def obtener_por_asignacion_y_estudiante(
        self, id_asignacion: UUID, id_estudiante: int
    ) -> Optional[EntregaActividad]:
        m = (
            EntregaActividadModel.objects.select_related("estudiante", "asignacion")
            .filter(asignacion_id=id_asignacion, estudiante_id=id_estudiante)
            .first()
        )
        return self._a_entidad(m) if m else None

    def listar_por_asignacion(self, id_asignacion: UUID) -> List[EntregaActividad]:
        return [
            self._a_entidad(m)
            for m in EntregaActividadModel.objects.select_related("estudiante")
            .filter(asignacion_id=id_asignacion)
            .order_by("-actualizada_en")
        ]

    def listar_por_estudiante(self, id_estudiante: int) -> List[EntregaActividad]:
        return [
            self._a_entidad(m)
            for m in EntregaActividadModel.objects.select_related("asignacion__actividad")
            .filter(estudiante_id=id_estudiante)
            .order_by("-actualizada_en")
        ]

    def guardar(self, entrega: EntregaActividad) -> EntregaActividad:
        m, _ = EntregaActividadModel.objects.update_or_create(
            id=entrega.id,
            defaults={
                "asignacion_id": entrega.asignacion_id,
                "estudiante_id": entrega.estudiante_id,
                "estado": entrega.estado,
                "solucion_texto": entrega.solucion_texto,
                "hechos_ingresados": entrega.hechos_ingresados,
                "ejecucion_inferencia_id": entrega.ejecucion_inferencia_id,
                "fecha_envio": entrega.fecha_envio,
            },
        )
        return self._a_entidad(m)
