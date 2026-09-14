"""
Vistas de API REST para el módulo de Editor Visual.
"""
from uuid import UUID
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.editor_visual.serializers import (
    ConexionVisualEntradaSerializer,
    ConexionVisualSalidaSerializer,
    EditorVisualSalidaSerializer,
    NodoVisualEntradaSerializer,
    NodoVisualMoverEntradaSerializer,
    NodoVisualSalidaSerializer,
)
from apps.editor_visual.services import (
    CrearConexionVisual,
    CrearNodoVisual,
    EliminarConexionVisual,
    EliminarNodoVisual,
    MoverNodoVisual,
    ObtenerEditorVisual,
)
from compartido.respuestas.respuesta_api import respuesta_creada, respuesta_exitosa


class EditorVisualAPIView(APIView):
    """Consulta el estado del lienzo visual (nodos y conexiones) de un sistema experto."""

    @extend_schema(
        summary="Obtener lienzo del editor visual",
        description="Recupera todos los nodos gráficos y las conexiones correspondientes al sistema experto.",
        responses={
            200: EditorVisualSalidaSerializer,
            404: OpenApiResponse(description="No encontrado"),
        },
        tags=["Editor Visual"],
    )
    def get(self, request, id: UUID):
        caso_uso = ObtenerEditorVisual()
        editor = caso_uso.ejecutar(sistema_experto_id=id)
        datos = EditorVisualSalidaSerializer(editor).data
        return respuesta_exitosa(datos=datos, mensaje="Lienzo visual obtenido correctamente.")


class NodoVisualCreateAPIView(APIView):
    """Agregar un nodo gráfico al editor visual."""

    @extend_schema(
        summary="Crear nodo visual",
        description="Agrega un hecho, variable, condición, regla o conclusión al lienzo con sus coordenadas (X, Y).",
        request=NodoVisualEntradaSerializer,
        responses={
            201: NodoVisualSalidaSerializer,
            400: OpenApiResponse(description="Datos inválidos"),
        },
        tags=["Editor Visual"],
    )
    def post(self, request, id: UUID):
        serializer = NodoVisualEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = CrearNodoVisual()
        nodo = caso_uso.ejecutar(
            sistema_experto_id=id,
            tipo=serializer.validated_data["tipo"],
            referencia_id=serializer.validated_data["referencia_id"],
            posicion_x=serializer.validated_data.get("posicion_x", 0.0),
            posicion_y=serializer.validated_data.get("posicion_y", 0.0),
        )
        datos = NodoVisualSalidaSerializer(nodo).data
        return respuesta_creada(datos=datos, mensaje="Nodo visual agregado correctamente al lienzo.")


class NodoVisualDetailAPIView(APIView):
    """Mover o eliminar un nodo visual en el lienzo."""

    @extend_schema(
        summary="Mover nodo visual",
        description="Actualiza las coordenadas espaciales (X, Y) de un nodo visual.",
        request=NodoVisualMoverEntradaSerializer,
        responses={
            200: NodoVisualSalidaSerializer,
            400: OpenApiResponse(description="Datos inválidos"),
            404: OpenApiResponse(description="No encontrado"),
        },
        tags=["Editor Visual"],
    )
    def patch(self, request, id: UUID):
        serializer = NodoVisualMoverEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = MoverNodoVisual()
        nodo = caso_uso.ejecutar(
            id_nodo=id,
            posicion_x=serializer.validated_data["posicion_x"],
            posicion_y=serializer.validated_data["posicion_y"],
        )
        datos = NodoVisualSalidaSerializer(nodo).data
        return respuesta_exitosa(
            datos=datos, mensaje="Posición del nodo visual actualizada correctamente."
        )

    @extend_schema(
        summary="Eliminar nodo visual",
        description="Elimina un nodo del lienzo y sus conexiones asociadas.",
        responses={
            204: OpenApiResponse(description="Eliminado exitosamente"),
            404: OpenApiResponse(description="No encontrado"),
        },
        tags=["Editor Visual"],
    )
    def delete(self, request, id: UUID):
        caso_uso = EliminarNodoVisual()
        caso_uso.ejecutar(id_nodo=id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConexionVisualCreateAPIView(APIView):
    """Conectar dos nodos visuales en el editor."""

    @extend_schema(
        summary="Crear conexión visual",
        description="Establece una relación dirigida entre un nodo origen y un nodo destino del mismo sistema experto.",
        request=ConexionVisualEntradaSerializer,
        responses={
            201: ConexionVisualSalidaSerializer,
            400: OpenApiResponse(description="Datos inválidos"),
        },
        tags=["Editor Visual"],
    )
    def post(self, request, id: UUID):
        serializer = ConexionVisualEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caso_uso = CrearConexionVisual()
        conexion = caso_uso.ejecutar(
            sistema_experto_id=id,
            nodo_origen_id=serializer.validated_data["nodo_origen_id"],
            nodo_destino_id=serializer.validated_data["nodo_destino_id"],
            etiqueta=serializer.validated_data.get("etiqueta"),
            tipo=serializer.validated_data.get("tipo"),
        )
        datos = ConexionVisualSalidaSerializer(conexion).data
        return respuesta_creada(datos=datos, mensaje="Conexión visual creada correctamente.")


class ConexionVisualDetailAPIView(APIView):
    """Eliminar una conexión visual."""

    @extend_schema(
        summary="Eliminar conexión visual",
        description="Remueve una conexión entre nodos del lienzo.",
        responses={
            204: OpenApiResponse(description="Eliminada exitosamente"),
            404: OpenApiResponse(description="No encontrada"),
        },
        tags=["Editor Visual"],
    )
    def delete(self, request, id: UUID):
        caso_uso = EliminarConexionVisual()
        caso_uso.ejecutar(id_conexion=id)
        return Response(status=status.HTTP_204_NO_CONTENT)
