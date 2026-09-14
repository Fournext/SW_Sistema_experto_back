"""
Vistas de API REST para el módulo de Inferencia.
"""
from uuid import UUID
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.views import APIView

from apps.inferencia.serializers import (
    DetalleInferenciaSalidaSerializer,
    EjecucionInferenciaSalidaSerializer,
    EjecutarInferenciaSalidaSerializer,
)
from apps.inferencia.services import (
    ConsultarEjecucion,
    ConsultarTrazaInferencia,
    EjecutarInferencia,
)
from compartido.respuestas.respuesta_api import respuesta_creada, respuesta_exitosa


class InferenciaEjecutarAPIView(APIView):
    """Ejecuta el motor de inferencia para un sistema experto."""

    @extend_schema(
        summary="Ejecutar motor de inferencia",
        description=(
            "Ejecuta el ciclo de razonamiento por encadenamiento hacia adelante utilizando "
            "los hechos iniciales y las reglas activas de la base de conocimiento."
        ),
        request=None,
        responses={
            201: OpenApiResponse(
                response=EjecutarInferenciaSalidaSerializer,
                description="Inferencia completada",
            ),
            404: OpenApiResponse(description="Sistema experto no encontrado"),
            422: OpenApiResponse(description="Límite de iteraciones alcanzado"),
        },
        tags=["Inferencia"],
    )
    def post(self, request, id: UUID):
        caso_uso = EjecutarInferencia()
        resultado = caso_uso.ejecutar(sistema_experto_id=id)
        datos = EjecutarInferenciaSalidaSerializer(resultado).data
        return respuesta_creada(datos=datos, mensaje="Inferencia ejecutada correctamente.")


class EjecucionInferenciaDetailAPIView(APIView):
    """Consulta el estado general de una ejecución de inferencia."""

    @extend_schema(
        summary="Consultar ejecución de inferencia",
        description="Obtiene el resumen y estado final de una sesión de ejecución de inferencia.",
        responses={
            200: EjecucionInferenciaSalidaSerializer,
            404: OpenApiResponse(description="No encontrada"),
        },
        tags=["Inferencia"],
    )
    def get(self, request, id: UUID):
        caso_uso = ConsultarEjecucion()
        ejecucion = caso_uso.ejecutar(id_ejecucion=id)
        datos = EjecucionInferenciaSalidaSerializer(ejecucion).data
        return respuesta_exitosa(
            datos=datos, mensaje="Ejecución de inferencia obtenida correctamente."
        )


class DetalleInferenciaListAPIView(APIView):
    """Consulta la traza detallada de reglas de una ejecución de inferencia."""

    @extend_schema(
        summary="Consultar traza de inferencia",
        description="Obtiene todos los pasos detallados (EVALUADA, RECHAZADA, ACTIVADA, EJECUTADA) de una ejecución.",
        responses={
            200: DetalleInferenciaSalidaSerializer(many=True),
            404: OpenApiResponse(description="No encontrada"),
        },
        tags=["Inferencia"],
    )
    def get(self, request, id: UUID):
        caso_uso = ConsultarTrazaInferencia()
        detalles = caso_uso.ejecutar(id_ejecucion=id)
        datos = DetalleInferenciaSalidaSerializer(detalles, many=True).data
        return respuesta_exitosa(
            datos=datos, mensaje="Traza de inferencia obtenida correctamente."
        )
