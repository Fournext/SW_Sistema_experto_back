"""
Servicios y Casos de Uso para el módulo de Actividades Educativas (Sprint 2 - HU-23, HU-24, HU-25).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from apps.actividades.entities import (
    ActividadEducativa,
    AsignacionActividad,
    Curso,
    EntregaActividad,
)
from apps.actividades.models import CursoModel
from apps.actividades.repositories import (
    ActividadEducativaRepositorio,
    AsignacionActividadRepositorio,
    CursoRepositorio,
    DjangoActividadEducativaRepositorio,
    DjangoAsignacionActividadRepositorio,
    DjangoCursoRepositorio,
    DjangoEntregaActividadRepositorio,
    EntregaActividadRepositorio,
)
from apps.sistemas_expertos.models import SistemaExpertoModel
from compartido.constantes.enums import (
    DificultadActividad,
    EstadoActividad,
    EstadoAsignacion,
    EstadoEntrega,
)
from compartido.excepciones.base import (
    ExcepcionEntidadNoEncontrada,
    ExcepcionValidacionDominio,
)


class CrearCurso:
    """Caso de uso: Crear un curso académico mínimo (soporte Sprint 2)."""

    def __init__(self, repositorio: Optional[CursoRepositorio] = None):
        self.repositorio = repositorio or DjangoCursoRepositorio()

    def ejecutar(
        self,
        codigo: str,
        nombre: str,
        docente_id: int,
        descripcion: Optional[str] = None,
    ) -> Curso:
        codigo = (codigo or "").strip().upper()
        nombre = (nombre or "").strip()
        if not codigo:
            raise ExcepcionValidacionDominio("El código del curso es obligatorio.")
        if not nombre:
            raise ExcepcionValidacionDominio("El nombre del curso es obligatorio.")

        if CursoModel.objects.filter(codigo=codigo).exists():
            raise ExcepcionValidacionDominio(f"Ya existe un curso con el código '{codigo}'.")

        curso = Curso(
            codigo=codigo,
            nombre=nombre,
            descripcion=descripcion,
            docente_id=docente_id,
            activo=True,
        )
        return self.repositorio.guardar(curso)


class ListarCursos:
    """Caso de uso: Listar cursos académicos."""

    def __init__(self, repositorio: Optional[CursoRepositorio] = None):
        self.repositorio = repositorio or DjangoCursoRepositorio()

    def ejecutar(self, docente_id: Optional[int] = None) -> List[Curso]:
        return self.repositorio.listar(docente_id=docente_id, solo_activos=True)


class CrearActividadEducativa:
    """Caso de uso: Crear una actividad educativa asociada a un sistema experto (HU-23)."""

    def __init__(self, repositorio: Optional[ActividadEducativaRepositorio] = None):
        self.repositorio = repositorio or DjangoActividadEducativaRepositorio()

    def ejecutar(
        self,
        docente_id: int,
        sistema_experto_id: UUID,
        titulo: str,
        instrucciones: str,
        dificultad: str = DificultadActividad.MEDIA.value,
        estado: str = EstadoActividad.BORRADOR.value,
    ) -> ActividadEducativa:
        titulo = (titulo or "").strip()
        instrucciones = (instrucciones or "").strip()
        if not titulo:
            raise ExcepcionValidacionDominio("El título de la actividad es obligatorio.")
        if not instrucciones:
            raise ExcepcionValidacionDominio("Las instrucciones didácticas son obligatorias.")

        if not SistemaExpertoModel.objects.filter(id=sistema_experto_id).exists():
            raise ExcepcionEntidadNoEncontrada(
                f"No se encontró el sistema experto con ID '{sistema_experto_id}'."
            )

        actividad = ActividadEducativa(
            docente_id=docente_id,
            sistema_experto_id=sistema_experto_id,
            titulo=titulo,
            instrucciones=instrucciones,
            dificultad=dificultad,
            estado=estado,
            activa=True,
        )
        return self.repositorio.guardar(actividad)


class ActualizarActividadEducativa:
    """Caso de uso: Actualizar una actividad educativa existente (HU-23)."""

    def __init__(self, repositorio: Optional[ActividadEducativaRepositorio] = None):
        self.repositorio = repositorio or DjangoActividadEducativaRepositorio()

    def ejecutar(
        self,
        id_actividad: UUID,
        docente_id: int,
        titulo: Optional[str] = None,
        instrucciones: Optional[str] = None,
        dificultad: Optional[str] = None,
        estado: Optional[str] = None,
    ) -> ActividadEducativa:
        actividad = self.repositorio.obtener_por_id(id_actividad)
        if not actividad or not actividad.activa:
            raise ExcepcionEntidadNoEncontrada(f"Actividad con ID '{id_actividad}' no encontrada.")

        # Verificar permisos (solo el docente responsable puede editar)
        if actividad.docente_id != docente_id:
            raise ExcepcionValidacionDominio(
                "No tiene permisos para modificar esta actividad educativa."
            )

        if titulo is not None:
            titulo = titulo.strip()
            if not titulo:
                raise ExcepcionValidacionDominio("El título no puede estar vacío.")
            actividad.titulo = titulo

        if instrucciones is not None:
            instrucciones = instrucciones.strip()
            if not instrucciones:
                raise ExcepcionValidacionDominio("Las instrucciones no pueden estar vacías.")
            actividad.instrucciones = instrucciones

        if dificultad is not None:
            actividad.dificultad = dificultad.upper()

        if estado is not None:
            actividad.estado = estado.upper()

        return self.repositorio.guardar(actividad)


class DesactivarActividadEducativa:
    """Caso de uso: Desactivar una actividad educativa (baja lógica) (HU-23)."""

    def __init__(self, repositorio: Optional[ActividadEducativaRepositorio] = None):
        self.repositorio = repositorio or DjangoActividadEducativaRepositorio()

    def ejecutar(self, id_actividad: UUID, docente_id: int) -> bool:
        actividad = self.repositorio.obtener_por_id(id_actividad)
        if not actividad:
            raise ExcepcionEntidadNoEncontrada(f"Actividad con ID '{id_actividad}' no encontrada.")

        if actividad.docente_id != docente_id:
            raise ExcepcionValidacionDominio(
                "No tiene permisos para desactivar esta actividad educativa."
            )

        return self.repositorio.desactivar(id_actividad)


class ConsultarActividadEducativa:
    """Caso de uso: Consultar el detalle de una actividad (HU-23)."""

    def __init__(self, repositorio: Optional[ActividadEducativaRepositorio] = None):
        self.repositorio = repositorio or DjangoActividadEducativaRepositorio()

    def ejecutar(self, id_actividad: UUID) -> ActividadEducativa:
        actividad = self.repositorio.obtener_por_id(id_actividad)
        if not actividad or not actividad.activa:
            raise ExcepcionEntidadNoEncontrada(f"Actividad con ID '{id_actividad}' no encontrada.")
        return actividad


class ListarActividadesDocente:
    """Caso de uso: Listar las actividades creadas por un docente (HU-23)."""

    def __init__(self, repositorio: Optional[ActividadEducativaRepositorio] = None):
        self.repositorio = repositorio or DjangoActividadEducativaRepositorio()

    def ejecutar(
        self,
        docente_id: Optional[int] = None,
        estado: Optional[str] = None,
    ) -> List[ActividadEducativa]:
        return self.repositorio.listar(docente_id=docente_id, estado=estado, solo_activas=True)


class AsignarActividadACurso:
    """Caso de uso: Asignar una actividad a un curso académico (HU-24)."""

    def __init__(
        self,
        actividad_repo: Optional[ActividadEducativaRepositorio] = None,
        curso_repo: Optional[CursoRepositorio] = None,
        asignacion_repo: Optional[AsignacionActividadRepositorio] = None,
    ):
        self.actividad_repo = actividad_repo or DjangoActividadEducativaRepositorio()
        self.curso_repo = curso_repo or DjangoCursoRepositorio()
        self.asignacion_repo = asignacion_repo or DjangoAsignacionActividadRepositorio()

    def ejecutar(
        self,
        id_actividad: UUID,
        id_curso: UUID,
        docente_id: int,
        fecha_limite: Optional[datetime] = None,
    ) -> AsignacionActividad:
        actividad = self.actividad_repo.obtener_por_id(id_actividad)
        if not actividad or not actividad.activa:
            raise ExcepcionEntidadNoEncontrada(f"Actividad '{id_actividad}' no encontrada.")

        curso = self.curso_repo.obtener_por_id(id_curso)
        if not curso or not curso.activo:
            raise ExcepcionEntidadNoEncontrada(f"Curso '{id_curso}' no encontrado.")

        # Verificar si ya existe asignación entre esta actividad y este curso
        existente = self.asignacion_repo.obtener_por_actividad_y_curso(id_actividad, id_curso)
        if existente:
            raise ExcepcionValidacionDominio(
                "Esta actividad ya ha sido asignada previamente a este curso."
            )

        asignacion = AsignacionActividad(
            actividad_id=id_actividad,
            curso_id=id_curso,
            fecha_limite=fecha_limite,
            estado=EstadoAsignacion.VIGENTE.value,
        )
        return self.asignacion_repo.guardar(asignacion)


class ListarAsignaciones:
    """Caso de uso: Listar asignaciones filtradas por curso o actividad (HU-24)."""

    def __init__(self, repositorio: Optional[AsignacionActividadRepositorio] = None):
        self.repositorio = repositorio or DjangoAsignacionActividadRepositorio()

    def ejecutar(
        self,
        curso_id: Optional[UUID] = None,
        actividad_id: Optional[UUID] = None,
        estado: Optional[str] = None,
    ) -> List[AsignacionActividad]:
        return self.repositorio.listar(curso_id=curso_id, actividad_id=actividad_id, estado=estado)


class ListarActividadesParaEstudiante:
    """
    Caso de uso: Obtener el catálogo de actividades asignadas disponibles para un estudiante (HU-25).
    Retorna la lista de asignaciones vigentes enriquecidas con el estado de entrega del estudiante.
    """

    def __init__(
        self,
        asignacion_repo: Optional[AsignacionActividadRepositorio] = None,
        entrega_repo: Optional[EntregaActividadRepositorio] = None,
    ):
        self.asignacion_repo = asignacion_repo or DjangoAsignacionActividadRepositorio()
        self.entrega_repo = entrega_repo or DjangoEntregaActividadRepositorio()

    def ejecutar(self, estudiante_id: int) -> List[Dict[str, Any]]:
        asignaciones = self.asignacion_repo.listar(estado=EstadoAsignacion.VIGENTE.value)
        resultado = []
        for asig in asignaciones:
            entrega = self.entrega_repo.obtener_por_asignacion_y_estudiante(asig.id, estudiante_id)
            resultado.append(
                {
                    "asignacion_id": asig.id,
                    "actividad_id": asig.actividad_id,
                    "actividad_titulo": asig.actividad_titulo,
                    "curso_id": asig.curso_id,
                    "curso_codigo": asig.curso_codigo,
                    "curso_nombre": asig.curso_nombre,
                    "fecha_asignacion": asig.fecha_asignacion,
                    "fecha_limite": asig.fecha_limite,
                    "estado_asignacion": asig.estado,
                    "tiene_entrega": entrega is not None,
                    "estado_entrega": entrega.estado if entrega else "PENDIENTE",
                    "entrega_id": entrega.id if entrega else None,
                }
            )
        return resultado


class GuardarBorradorEntrega:
    """Caso de uso: Guardar un borrador de solución de un estudiante (HU-25)."""

    def __init__(
        self,
        asignacion_repo: Optional[AsignacionActividadRepositorio] = None,
        entrega_repo: Optional[EntregaActividadRepositorio] = None,
    ):
        self.asignacion_repo = asignacion_repo or DjangoAsignacionActividadRepositorio()
        self.entrega_repo = entrega_repo or DjangoEntregaActividadRepositorio()

    def ejecutar(
        self,
        id_asignacion: UUID,
        estudiante_id: int,
        solucion_texto: Optional[str] = None,
        hechos_ingresados: Optional[List[Dict[str, Any]]] = None,
        ejecucion_inferencia_id: Optional[UUID] = None,
    ) -> EntregaActividad:
        asig = self.asignacion_repo.obtener_por_id(id_asignacion)
        if not asig:
            raise ExcepcionEntidadNoEncontrada(f"Asignación '{id_asignacion}' no encontrada.")

        entrega = self.entrega_repo.obtener_por_asignacion_y_estudiante(id_asignacion, estudiante_id)
        if entrega and entrega.estado == EstadoEntrega.ENVIADA.value:
            raise ExcepcionValidacionDominio(
                "Esta actividad ya ha sido enviada definitivamente y no admite modificaciones."
            )

        if not entrega:
            entrega = EntregaActividad(
                asignacion_id=id_asignacion,
                estudiante_id=estudiante_id,
                estado=EstadoEntrega.BORRADOR.value,
            )

        entrega.solucion_texto = solucion_texto
        entrega.hechos_ingresados = hechos_ingresados or []
        entrega.ejecucion_inferencia_id = ejecucion_inferencia_id
        entrega.estado = EstadoEntrega.BORRADOR.value
        return self.entrega_repo.guardar(entrega)


class EnviarEntrega:
    """Caso de uso: Enviar definitivamente la entrega de una actividad (HU-25)."""

    def __init__(
        self,
        asignacion_repo: Optional[AsignacionActividadRepositorio] = None,
        entrega_repo: Optional[EntregaActividadRepositorio] = None,
    ):
        self.asignacion_repo = asignacion_repo or DjangoAsignacionActividadRepositorio()
        self.entrega_repo = entrega_repo or DjangoEntregaActividadRepositorio()

    def ejecutar(
        self,
        id_asignacion: UUID,
        estudiante_id: int,
        solucion_texto: Optional[str] = None,
        hechos_ingresados: Optional[List[Dict[str, Any]]] = None,
        ejecucion_inferencia_id: Optional[UUID] = None,
    ) -> EntregaActividad:
        asig = self.asignacion_repo.obtener_por_id(id_asignacion)
        if not asig:
            raise ExcepcionEntidadNoEncontrada(f"Asignación '{id_asignacion}' no encontrada.")

        entrega = self.entrega_repo.obtener_por_asignacion_y_estudiante(id_asignacion, estudiante_id)
        if entrega and entrega.estado == EstadoEntrega.ENVIADA.value:
            raise ExcepcionValidacionDominio("La entrega ya fue enviada previamente.")

        if not entrega:
            entrega = EntregaActividad(
                asignacion_id=id_asignacion,
                estudiante_id=estudiante_id,
            )

        if not solucion_texto and not hechos_ingresados and not ejecucion_inferencia_id:
            raise ExcepcionValidacionDominio(
                "Debe proporcionar una justificación de solución o hechos configurados."
            )

        entrega.solucion_texto = solucion_texto
        entrega.hechos_ingresados = hechos_ingresados or []
        entrega.ejecucion_inferencia_id = ejecucion_inferencia_id
        entrega.estado = EstadoEntrega.ENVIADA.value
        entrega.fecha_envio = datetime.now(timezone.utc)
        return self.entrega_repo.guardar(entrega)


class ConsultarEntregaEstudiante:
    """
    Caso de uso: Consultar la entrega de un estudiante garantizando aislamiento de datos (IDOR protection).
    - Un estudiante SOLO puede consultar su propia entrega.
    - Un docente puede consultar las entregas de su asignación.
    """

    def __init__(self, entrega_repo: Optional[EntregaActividadRepositorio] = None):
        self.entrega_repo = entrega_repo or DjangoEntregaActividadRepositorio()

    def ejecutar(
        self,
        id_asignacion: UUID,
        usuario_id: int,
        es_docente: bool = False,
        estudiante_objetivo_id: Optional[int] = None,
    ) -> Optional[EntregaActividad]:
        id_estudiante_a_consultar = (
            estudiante_objetivo_id if (es_docente and estudiante_objetivo_id) else usuario_id
        )
        return self.entrega_repo.obtener_por_asignacion_y_estudiante(
            id_asignacion, id_estudiante_a_consultar
        )
