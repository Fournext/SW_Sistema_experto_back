"""
Vistas de API REST para Sistemas Expertos.
Controladores delegados en la capa de servicios.
"""
from uuid import UUID
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

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

    @extend_schema(
        summary="Listar sistemas expertos",
        description="Obtiene la lista de todos los sistemas expertos registrados por el docente.",
        responses={200: SistemaExpertoSalidaSerializer(many=True)},
        tags=["Sistemas Expertos"],
    )
    def get(self, request):
        caso_uso = ListarSistemasExpertos()
        sistemas = caso_uso.ejecutar()
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
        datos = SistemaExpertoSalidaSerializer(sistema).data
        return respuesta_creada(datos=datos, mensaje="Sistema experto creado correctamente.")


class SistemaExpertoDetailAPIView(APIView):
    """Consultar, actualizar o eliminar un sistema experto por su ID."""

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
