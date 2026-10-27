"""
Vistas de API REST para el módulo de Validación de Bases de Conocimiento.
"""
from uuid import UUID
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView

from apps.validacion.serializers import (
    IncidenciaValidacionSalidaSerializer,
    ValidacionBaseSalidaSerializer,
)
from apps.validacion.services import (
    ConsultarIncidenciasValidacion,
    ConsultarUltimaValidacion,
    ConsultarValidacion,
    ValidarBaseConocimiento,
)
from compartido.respuestas.respuesta_api import respuesta_creada, respuesta_error, respuesta_exitosa


class BaseConocimientoValidarAPIView(APIView):
    """Ejecuta la validación analítica de una base de conocimiento (HU-18)."""

    @extend_schema(
        summary="Validar base de conocimiento",
        description="Analiza reglas duplicadas, contradictorias, referencias rotas, variables huérfanas y tipos incompatibles.",
        request=None,
        responses={
            201: ValidacionBaseSalidaSerializer,
            404: OpenApiResponse(description="Base de conocimiento no encontrada"),
        },
        tags=["Validación de Conocimiento"],
    )
    def post(self, request, id: UUID):
        caso_uso = ValidarBaseConocimiento()
        resultado = caso_uso.ejecutar(base_conocimiento_id=id)
        datos = ValidacionBaseSalidaSerializer(resultado).data
        return respuesta_creada(datos=datos, mensaje="Validación completada.")


class UltimaValidacionAPIView(APIView):
    """Consulta el último reporte de validación ejecutado para una base de conocimiento (HU-18, HU-19)."""

    @extend_schema(
        summary="Consultar última validación de una base",
        responses={
            200: ValidacionBaseSalidaSerializer,
            404: OpenApiResponse(description="No existen validaciones previas"),
        },
        tags=["Validación de Conocimiento"],
    )
    def get(self, request, id: UUID):
        caso_uso = ConsultarUltimaValidacion()
        resultado = caso_uso.ejecutar(base_conocimiento_id=id)
        if not resultado:
            return respuesta_error(
                mensaje="No se encontró ninguna validación previa para esta base de conocimiento.",
                codigo_estado=status.HTTP_404_NOT_FOUND,
            )
        datos = ValidacionBaseSalidaSerializer(resultado).data
        return respuesta_exitosa(datos=datos, mensaje="Última validación obtenida.")


class ValidacionDetailAPIView(APIView):
    """Consulta el detalle de una validación por su ID."""

    @extend_schema(
        summary="Consultar validación por ID",
        responses={
            200: ValidacionBaseSalidaSerializer,
            404: OpenApiResponse(description="Validación no encontrada"),
        },
        tags=["Validación de Conocimiento"],
    )
    def get(self, request, id: UUID):
        caso_uso = ConsultarValidacion()
        resultado = caso_uso.ejecutar(id_validacion=id)
        if not resultado:
            return respuesta_error(
                mensaje="Validación no encontrada.",
                codigo_estado=status.HTTP_404_NOT_FOUND,
            )
        datos = ValidacionBaseSalidaSerializer(resultado).data
        return respuesta_exitosa(datos=datos, mensaje="Validación obtenida.")


class IncidenciasListAPIView(APIView):
    """Consulta el reporte detallado de incidencias y sugerencias con filtros (HU-19)."""

    @extend_schema(
        summary="Consultar reporte de incidencias",
        parameters=[
            OpenApiParameter("severidad", type=str, description="ERROR o ADVERTENCIA"),
            OpenApiParameter("tipo", type=str, description="ESTRUCTURAL, SEMANTICA, REFERENCIAL, CICLO"),
        ],
        responses={200: IncidenciaValidacionSalidaSerializer(many=True)},
        tags=["Validación de Conocimiento"],
    )
    def get(self, request, id: UUID):
        severidad = request.query_params.get("severidad")
        tipo = request.query_params.get("tipo")
        caso_uso = ConsultarIncidenciasValidacion()
        incidencias = caso_uso.ejecutar(
            id_validacion=id, severidad=severidad, tipo=tipo
        )
        datos = IncidenciaValidacionSalidaSerializer(incidencias, many=True).data
        return respuesta_exitosa(datos=datos, mensaje="Incidencias obtenidas.")
