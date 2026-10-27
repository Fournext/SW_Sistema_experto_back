"""
Estructura uniforme de respuestas HTTP para la API REST.
"""
from typing import Any, Optional
from rest_framework.response import Response
from rest_framework import status


def respuesta_exitosa(
    datos: Any = None,
    mensaje: str = "Operación realizada con éxito.",
    codigo_estado: int = status.HTTP_200_OK,
) -> Response:
    """Genera una respuesta JSON estándar exitosa."""
    cuerpo = {
        "success": True,
        "message": mensaje,
        "data": datos if datos is not None else {},
    }
    return Response(cuerpo, status=codigo_estado)


def respuesta_creada(
    datos: Any = None,
    mensaje: str = "Recurso creado correctamente.",
) -> Response:
    """Genera una respuesta JSON estándar con status 201 CREATED."""
    return respuesta_exitosa(datos=datos, mensaje=mensaje, codigo_estado=status.HTTP_201_CREATED)


def respuesta_error(
    mensaje: str = "Ocurrió un error al procesar la solicitud.",
    errores: Optional[Any] = None,
    codigo_estado: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """Genera una respuesta JSON estándar de error."""
    cuerpo = {
        "success": False,
        "message": mensaje,
        "errors": errores if errores is not None else {},
    }
    return Response(cuerpo, status=codigo_estado)


class RespuestaAPI:
    """Adaptador estático orientado a objetos para generar respuestas uniformes."""

    @staticmethod
    def exito(
        data: Any = None,
        mensaje: str = "Operación realizada con éxito.",
        codigo_estado: int = status.HTTP_200_OK,
    ) -> Response:
        return respuesta_exitosa(datos=data, mensaje=mensaje, codigo_estado=codigo_estado)

    @staticmethod
    def error(
        mensaje: str = "Ocurrió un error al procesar la solicitud.",
        errores: Optional[Any] = None,
        codigo_estado: int = status.HTTP_400_BAD_REQUEST,
    ) -> Response:
        return respuesta_error(mensaje=mensaje, errores=errores, codigo_estado=codigo_estado)

