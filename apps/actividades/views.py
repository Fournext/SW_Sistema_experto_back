"""
Vistas de API REST para el módulo de Actividades Educativas (Sprint 2 - HU-23, HU-24, HU-25).
"""
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView
from apps.permisos.visibilidad import puede_ver_borradores
from apps.actividades.models import ActividadEducativaModel, AsignacionActividadModel

from apps.actividades.serializers import (
    ActividadEducativaSerializer,
    ActividadEstudianteResumenSerializer,
    ActualizarActividadEducativaSerializer,
    AsignacionActividadSerializer,
    CrearActividadEducativaSerializer,
    CrearAsignacionActividadSerializer,
    CrearCursoSerializer,
    CursoSerializer,
    EntregaActividadSerializer,
    EnviarEntregaSerializer,
    GuardarBorradorEntregaSerializer,
)
from apps.actividades.services import (
    ActualizarActividadEducativa,
    AsignarActividadACurso,
    ConsultarActividadEducativa,
    ConsultarEntregaEstudiante,
    CrearActividadEducativa,
    CrearCurso,
    DesactivarActividadEducativa,
    EnviarEntrega,
    GuardarBorradorEntrega,
    ListarActividadesDocente,
    ListarActividadesParaEstudiante,
    ListarAsignaciones,
    ListarCursos,
)
from compartido.respuestas.respuesta_api import respuesta_creada, respuesta_exitosa


class CursoListCreateAPIView(APIView):
    """Listar o crear cursos académicos mínimos."""

    @extend_schema(
        summary="Listar cursos",
        description="Retorna la lista de cursos registrados.",
        responses={200: CursoSerializer(many=True)},
        tags=["Actividades - Cursos"],
    )
    def get(self, request):
        docente_id = request.user.id if request.user.is_authenticated else None
        cursos = ListarCursos().ejecutar(docente_id=docente_id)
        datos = CursoSerializer(cursos, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Cursos listados correctamente.")

    @extend_schema(
        summary="Crear curso",
        description="Crea un curso académico para asignar actividades.",
        request=CrearCursoSerializer,
        responses={201: CursoSerializer},
        tags=["Actividades - Cursos"],
    )
    def post(self, request):
        serializer = CrearCursoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        docente_id = request.user.id if request.user.is_authenticated else 1

        curso = CrearCurso().ejecutar(
            codigo=serializer.validated_data["codigo"],
            nombre=serializer.validated_data["nombre"],
            descripcion=serializer.validated_data.get("descripcion"),
            docente_id=docente_id,
        )
        datos = CursoSerializer(curso).data
        return respuesta_creada(datos=datos, mensaje="Curso creado exitosamente.")


class ActividadListCreateAPIView(APIView):
    """HU-23: Listar y crear actividades educativas."""

    @extend_schema(
        summary="Listar actividades educativas",
        description="Retorna las actividades didácticas creadas.",
        parameters=[
            OpenApiParameter("estado", str, description="Filtrar por estado"),
        ],
        responses={200: ActividadEducativaSerializer(many=True)},
        tags=["Actividades Educativas"],
    )
    def get(self, request):
        docente_id = request.user.id if request.user.is_authenticated else None
        estado = request.query_params.get("estado")
        actividades = ListarActividadesDocente().ejecutar(docente_id=docente_id, estado=estado)
        if not puede_ver_borradores(request):
            visibles = set(ActividadEducativaModel.objects.filter(id__in=[a.id for a in actividades])
                           .exclude(sistema_experto__estado="BORRADOR").values_list("id", flat=True))
            actividades = [a for a in actividades if a.id in visibles]
        datos = ActividadEducativaSerializer(actividades, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Actividades listadas correctamente.")

    @extend_schema(
        summary="Crear actividad educativa (HU-23)",
        description="Permite al docente crear una nueva actividad asociada a un sistema experto.",
        request=CrearActividadEducativaSerializer,
        responses={201: ActividadEducativaSerializer},
        tags=["Actividades Educativas"],
    )
    def post(self, request):
        serializer = CrearActividadEducativaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        docente_id = request.user.id if request.user.is_authenticated else 1

        actividad = CrearActividadEducativa().ejecutar(
            docente_id=docente_id,
            sistema_experto_id=serializer.validated_data["sistema_experto_id"],
            titulo=serializer.validated_data["titulo"],
            instrucciones=serializer.validated_data["instrucciones"],
            dificultad=serializer.validated_data.get("dificultad", "MEDIA"),
            estado=serializer.validated_data.get("estado", "BORRADOR"),
        )
        datos = ActividadEducativaSerializer(actividad).data
        return respuesta_creada(datos=datos, mensaje="Actividad educativa creada exitosamente.")


class ActividadDetailAPIView(APIView):
    """HU-23: Consultar, actualizar y desactivar una actividad educativa."""

    @extend_schema(
        summary="Consultar actividad educativa",
        responses={200: ActividadEducativaSerializer},
        tags=["Actividades Educativas"],
    )
    def get(self, request, id_actividad: UUID):
        actividad = ConsultarActividadEducativa().ejecutar(id_actividad=id_actividad)
        datos = ActividadEducativaSerializer(actividad).data
        return respuesta_exitosa(datos=datos, mensaje="Actividad consultada exitosamente.")

    @extend_schema(
        summary="Actualizar actividad educativa",
        request=ActualizarActividadEducativaSerializer,
        responses={200: ActividadEducativaSerializer},
        tags=["Actividades Educativas"],
    )
    def put(self, request, id_actividad: UUID):
        serializer = ActualizarActividadEducativaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        docente_id = request.user.id if request.user.is_authenticated else 1

        actividad = ActualizarActividadEducativa().ejecutar(
            id_actividad=id_actividad,
            docente_id=docente_id,
            titulo=serializer.validated_data.get("titulo"),
            instrucciones=serializer.validated_data.get("instrucciones"),
            dificultad=serializer.validated_data.get("dificultad"),
            estado=serializer.validated_data.get("estado"),
        )
        datos = ActividadEducativaSerializer(actividad).data
        return respuesta_exitosa(datos=datos, mensaje="Actividad educativa actualizada exitosamente.")

    @extend_schema(
        summary="Desactivar actividad educativa",
        responses={200: OpenApiResponse(description="Actividad desactivada")},
        tags=["Actividades Educativas"],
    )
    def delete(self, request, id_actividad: UUID):
        docente_id = request.user.id if request.user.is_authenticated else 1
        DesactivarActividadEducativa().ejecutar(id_actividad=id_actividad, docente_id=docente_id)
        return respuesta_exitosa(datos=None, mensaje="Actividad desactivada exitosamente.")


class AsignacionListCreateAPIView(APIView):
    """HU-24: Listar y crear asignaciones de actividades a cursos."""

    @extend_schema(
        summary="Listar asignaciones (HU-24)",
        parameters=[
            OpenApiParameter("curso_id", str, description="ID del curso"),
            OpenApiParameter("actividad_id", str, description="ID de la actividad"),
        ],
        responses={200: AsignacionActividadSerializer(many=True)},
        tags=["Asignación de Actividades"],
    )
    def get(self, request):
        curso_id = request.query_params.get("curso_id")
        actividad_id = request.query_params.get("actividad_id")
        asignaciones = ListarAsignaciones().ejecutar(
            curso_id=UUID(curso_id) if curso_id else None,
            actividad_id=UUID(actividad_id) if actividad_id else None,
        )
        if not puede_ver_borradores(request):
            visibles = set(AsignacionActividadModel.objects.filter(id__in=[a.id for a in asignaciones])
                           .exclude(actividad__sistema_experto__estado="BORRADOR").values_list("id", flat=True))
            asignaciones = [a for a in asignaciones if a.id in visibles]
        datos = AsignacionActividadSerializer(asignaciones, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Asignaciones listadas correctamente.")

    @extend_schema(
        summary="Asignar actividad a curso (HU-24)",
        request=CrearAsignacionActividadSerializer,
        responses={201: AsignacionActividadSerializer},
        tags=["Asignación de Actividades"],
    )
    def post(self, request):
        serializer = CrearAsignacionActividadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        docente_id = request.user.id if request.user.is_authenticated else 1

        asignacion = AsignarActividadACurso().ejecutar(
            id_actividad=serializer.validated_data["actividad_id"],
            id_curso=serializer.validated_data["curso_id"],
            docente_id=docente_id,
            fecha_limite=serializer.validated_data.get("fecha_limite"),
        )
        datos = AsignacionActividadSerializer(asignacion).data
        return respuesta_creada(datos=datos, mensaje="Actividad asignada al curso exitosamente.")


class EstudianteActividadesListAPIView(APIView):
    """HU-25: Consultar catálogo de actividades asignadas para el estudiante."""

    @extend_schema(
        summary="Listar actividades asignadas al estudiante (HU-25)",
        responses={200: ActividadEstudianteResumenSerializer(many=True)},
        tags=["Resolución de Actividades"],
    )
    def get(self, request):
        estudiante_id = request.user.id if request.user.is_authenticated else 1
        resumenes = ListarActividadesParaEstudiante().ejecutar(estudiante_id=estudiante_id)
        if not puede_ver_borradores(request):
            visibles = set(AsignacionActividadModel.objects.filter(id__in=[r["asignacion_id"] for r in resumenes])
                           .exclude(actividad__sistema_experto__estado="BORRADOR").values_list("id", flat=True))
            resumenes = [r for r in resumenes if r["asignacion_id"] in visibles]
        datos = ActividadEstudianteResumenSerializer(resumenes, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Actividades de estudiante obtenidas.")


class EntregaEstudianteAPIView(APIView):
    """HU-25: Consultar o guardar borrador de la solución del estudiante."""

    @extend_schema(
        summary="Consultar entrega del estudiante",
        responses={200: EntregaActividadSerializer},
        tags=["Resolución de Actividades"],
    )
    def get(self, request, id_asignacion: UUID):
        usuario_id = request.user.id if request.user.is_authenticated else 1
        es_docente = request.user.is_staff if request.user.is_authenticated else False
        estudiante_objetivo = request.query_params.get("estudiante_id")

        entrega = ConsultarEntregaEstudiante().ejecutar(
            id_asignacion=id_asignacion,
            usuario_id=usuario_id,
            es_docente=es_docente,
            estudiante_objetivo_id=int(estudiante_objetivo) if estudiante_objetivo else None,
        )
        if not entrega:
            return respuesta_exitosa(datos=None, mensaje="Aún no existe entrega registrada.")
        datos = EntregaActividadSerializer(entrega).data
        return respuesta_exitosa(datos=datos, mensaje="Entrega consultada exitosamente.")

    @extend_schema(
        summary="Guardar borrador de entrega (HU-25)",
        request=GuardarBorradorEntregaSerializer,
        responses={200: EntregaActividadSerializer},
        tags=["Resolución de Actividades"],
    )
    def post(self, request, id_asignacion: UUID):
        serializer = GuardarBorradorEntregaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estudiante_id = request.user.id if request.user.is_authenticated else 1

        entrega = GuardarBorradorEntrega().ejecutar(
            id_asignacion=id_asignacion,
            estudiante_id=estudiante_id,
            solucion_texto=serializer.validated_data.get("solucion_texto"),
            hechos_ingresados=serializer.validated_data.get("hechos_ingresados"),
            ejecucion_inferencia_id=serializer.validated_data.get("ejecucion_inferencia_id"),
        )
        datos = EntregaActividadSerializer(entrega).data
        return respuesta_exitosa(datos=datos, mensaje="Borrador guardado correctamente.")


class EnviarEntregaAPIView(APIView):
    """HU-25: Enviar definitivamente la entrega de una actividad."""

    @extend_schema(
        summary="Enviar entrega de actividad (HU-25)",
        request=EnviarEntregaSerializer,
        responses={200: EntregaActividadSerializer},
        tags=["Resolución de Actividades"],
    )
    def post(self, request, id_asignacion: UUID):
        serializer = EnviarEntregaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estudiante_id = request.user.id if request.user.is_authenticated else 1

        entrega = EnviarEntrega().ejecutar(
            id_asignacion=id_asignacion,
            estudiante_id=estudiante_id,
            solucion_texto=serializer.validated_data.get("solucion_texto"),
            hechos_ingresados=serializer.validated_data.get("hechos_ingresados"),
            ejecucion_inferencia_id=serializer.validated_data.get("ejecucion_inferencia_id"),
        )
        datos = EntregaActividadSerializer(entrega).data
        return respuesta_exitosa(datos=datos, mensaje="Entrega enviada exitosamente.")
