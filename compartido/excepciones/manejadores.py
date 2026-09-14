"""
Manejador global de excepciones para Django REST Framework.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.exceptions import (
    ValidationError,
    NotFound,
    PermissionDenied,
    AuthenticationFailed,
    MethodNotAllowed,
)
from compartido.respuestas.respuesta_api import respuesta_error
from compartido.excepciones.base import (
    ExcepcionDominio,
    ExcepcionEntidadNoEncontrada,
    ExcepcionValidacionDominio,
    ExcepcionLimiteIteraciones,
)

logger = logging.getLogger("apps")


def manejador_excepciones_global(exc, context):
    """
    Transforma excepciones de DRF y excepciones de Dominio en respuestas
    uniformes JSON siguiendo el estándar del proyecto.
    """
    # 1. Manejo de excepciones de dominio personalizadas
    if isinstance(exc, ExcepcionEntidadNoEncontrada):
        logger.warning(f"Entidad no encontrada: {exc.mensaje}")
        return respuesta_error(
            mensaje=exc.mensaje,
            errores=exc.errores,
            codigo_estado=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, ExcepcionLimiteIteraciones):
        logger.error(f"Límite de iteraciones alcanzado: {exc.mensaje}")
        return respuesta_error(
            mensaje=exc.mensaje,
            errores=exc.errores,
            codigo_estado=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if isinstance(exc, ExcepcionValidacionDominio):
        logger.warning(f"Validación de dominio fallida: {exc.mensaje} - Errores: {exc.errores}")
        return respuesta_error(
            mensaje=exc.mensaje,
            errores=exc.errores,
            codigo_estado=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, ExcepcionDominio):
        logger.warning(f"Error de dominio: {exc.mensaje}")
        return respuesta_error(
            mensaje=exc.mensaje,
            errores=exc.errores,
            codigo_estado=status.HTTP_400_BAD_REQUEST,
        )

    # 2. Manejo de excepciones estándar de DRF
    respuesta = exception_handler(exc, context)

    if respuesta is not None:
        codigo = respuesta.status_code
        detalles = respuesta.data

        if isinstance(exc, ValidationError):
            mensaje = "Error de validación en los datos enviados."
            errores = detalles
        elif isinstance(exc, NotFound):
            mensaje = "El recurso solicitado no fue encontrado."
            errores = detalles
        elif isinstance(exc, MethodNotAllowed):
            mensaje = f"Método {context.get('request').method if context.get('request') else ''} no permitido."
            errores = detalles
        elif isinstance(exc, (PermissionDenied, AuthenticationFailed)):
            mensaje = "Acceso no autorizado."
            errores = detalles
        else:
            if isinstance(detalles, dict):
                mensaje = str(detalles.get("detail", "Error en la petición."))
            else:
                mensaje = str(detalles)
            errores = detalles

        return respuesta_error(
            mensaje=mensaje,
            errores=errores,
            codigo_estado=codigo,
        )

    # 3. Excepciones no controladas (500)
    logger.exception(f"Error interno no controlado: {str(exc)}", exc_info=exc)
    return respuesta_error(
        mensaje="Ocurrió un error interno en el servidor.",
        errores={"detalle": [str(exc)]},
        codigo_estado=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
