"""
Vistas de API REST para Sistemas Expertos.
Controladores delegados en la capa de servicios.
"""
from uuid import UUID
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.permisos.codigos import Permisos
from apps.permisos.guards import permisos_por_metodo
from apps.permisos.visibilidad import SistemaPublicadoPermission, puede_ver_borradores

from apps.sistemas_expertos.serializers import (
    SistemaExpertoEntradaSerializer,
    SistemaExpertoParcialEntradaSerializer,
    SistemaExpertoSalidaSerializer,
)
from apps.sistemas_expertos.services import (
    ActualizarSistemaExperto,
    CrearSistemaExperto,
    EliminarSistemaExperto,
    ListarSistemasExpertos,
    ObtenerSistemaExperto,
)
from compartido.respuestas.respuesta_api import respuesta_creada, respuesta_exitosa


class SistemaExpertoListCreateAPIView(APIView):
    """Listar todos los sistemas expertos o crear uno nuevo."""
    permission_classes = [SistemaPublicadoPermission, permisos_por_metodo({
        "GET": Permisos.SISTEMAS_VER, "POST": Permisos.SISTEMAS_CREAR,
        "HEAD": Permisos.SISTEMAS_VER, "OPTIONS": Permisos.SISTEMAS_VER,
    })]

    @extend_schema(
        summary="Listar sistemas expertos",
        description="Obtiene la lista de todos los sistemas expertos registrados por el docente.",
        responses={200: SistemaExpertoSalidaSerializer(many=True)},
        tags=["Sistemas Expertos"],
    )
    def get(self, request):
        caso_uso = ListarSistemasExpertos()
        sistemas = caso_uso.ejecutar()
        from apps.sistemas_expertos.models import SistemaExpertoModel
        from django.db.models import Q
        visibles = SistemaExpertoModel.objects.filter(trabajo_actividad__isnull=True)
        if puede_ver_borradores(request) and not request.user.is_superuser:
            visibles = visibles.filter(Q(created_by=request.user) | Q(created_by__isnull=True))
        ids = set(visibles.values_list("id", flat=True))
        sistemas = [s for s in sistemas if s.id in ids]
        if not puede_ver_borradores(request):
            ids = set(visibles.exclude(estado="BORRADOR").filter(actividades__isnull=True).values_list("id", flat=True))
            sistemas = [s for s in sistemas if s.id in ids]
        datos = SistemaExpertoSalidaSerializer(sistemas, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Sistemas expertos listados correctamente.")

    @extend_schema(
        summary="Crear sistema experto",
        description="Crea un nuevo sistema experto y genera automáticamente su base de conocimiento asociada.",
        request=SistemaExpertoEntradaSerializer,
        responses={
            201: OpenApiResponse(response=SistemaExpertoSalidaSerializer, description="Creado exitosamente"),
            400: OpenApiResponse(description="Datos inválidos"),
        },
        tags=["Sistemas Expertos"],
    )
    def post(self, request):
        serializer = SistemaExpertoEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = CrearSistemaExperto()
        sistema = caso_uso.ejecutar(
            nombre=serializer.validated_data["nombre"],
            descripcion=serializer.validated_data.get("descripcion"),
            estado=serializer.validated_data.get("estado"),
        )
        from apps.sistemas_expertos.models import SistemaExpertoModel
        SistemaExpertoModel.objects.filter(pk=sistema.id).update(created_by=request.user)
        datos = SistemaExpertoSalidaSerializer(sistema).data
        return respuesta_creada(datos=datos, mensaje="Sistema experto creado correctamente.")


class SistemaExpertoDetailAPIView(APIView):
    """Consultar, actualizar o eliminar un sistema experto por su ID."""
    permission_classes = [SistemaPublicadoPermission, permisos_por_metodo({
        "GET": Permisos.SISTEMAS_VER, "PUT": Permisos.SISTEMAS_EDITAR,
        "PATCH": Permisos.SISTEMAS_EDITAR, "DELETE": Permisos.SISTEMAS_ELIMINAR,
        "HEAD": Permisos.SISTEMAS_VER, "OPTIONS": Permisos.SISTEMAS_VER,
    })]

    @extend_schema(
        summary="Obtener sistema experto",
        description="Recupera la información detallada de un sistema experto por su UUID.",
        responses={
            200: SistemaExpertoSalidaSerializer,
            404: OpenApiResponse(description="No encontrado"),
        },
        tags=["Sistemas Expertos"],
    )
    def get(self, request, id: UUID):
        caso_uso = ObtenerSistemaExperto()
        sistema = caso_uso.ejecutar(id_sistema=id)
        datos = SistemaExpertoSalidaSerializer(sistema).data
        return respuesta_exitosa(datos=datos, mensaje="Sistema experto obtenido correctamente.")

    @extend_schema(
        summary="Actualizar sistema experto completamente",
        description="Actualiza todos los campos de un sistema experto.",
        request=SistemaExpertoEntradaSerializer,
        responses={
            200: SistemaExpertoSalidaSerializer,
            400: OpenApiResponse(description="Datos inválidos"),
            404: OpenApiResponse(description="No encontrado"),
        },
        tags=["Sistemas Expertos"],
    )
    def put(self, request, id: UUID):
        serializer = SistemaExpertoEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarSistemaExperto()
        sistema = caso_uso.ejecutar(
            id_sistema=id,
            nombre=serializer.validated_data["nombre"],
            descripcion=serializer.validated_data.get("descripcion"),
            estado=serializer.validated_data.get("estado"),
        )
        datos = SistemaExpertoSalidaSerializer(sistema).data
        return respuesta_exitosa(datos=datos, mensaje="Sistema experto actualizado correctamente.")

    @extend_schema(
        summary="Actualizar sistema experto parcialmente",
        description="Actualiza selectivamente los campos enviados de un sistema experto.",
        request=SistemaExpertoParcialEntradaSerializer,
        responses={
            200: SistemaExpertoSalidaSerializer,
            400: OpenApiResponse(description="Datos inválidos"),
            404: OpenApiResponse(description="No encontrado"),
        },
        tags=["Sistemas Expertos"],
    )
    def patch(self, request, id: UUID):
        serializer = SistemaExpertoParcialEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = ActualizarSistemaExperto()
        sistema = caso_uso.ejecutar(
            id_sistema=id,
            nombre=serializer.validated_data.get("nombre"),
            descripcion=serializer.validated_data.get("descripcion"),
            estado=serializer.validated_data.get("estado"),
        )
        datos = SistemaExpertoSalidaSerializer(sistema).data
        return respuesta_exitosa(datos=datos, mensaje="Sistema experto actualizado parcialmente.")

    @extend_schema(
        summary="Eliminar sistema experto",
        description="Elimina de forma permanente un sistema experto y todos sus elementos en cascada.",
        responses={
            204: OpenApiResponse(description="Eliminado sin contenido"),
            404: OpenApiResponse(description="No encontrado"),
        },
        tags=["Sistemas Expertos"],
    )
    def delete(self, request, id: UUID):
        caso_uso = EliminarSistemaExperto()
        caso_uso.ejecutar(id_sistema=id)
        return Response(status=status.HTTP_204_NO_CONTENT)
