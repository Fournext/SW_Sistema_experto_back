import logging
from typing import Type
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

_MENSAJE_GENERICO_DENEGADO = "No tiene permiso para realizar esta acción."


class PermisoRequerido(BasePermission):
    """
    Guardia base de DRF para verificación de permisos atómicos.
    Revisa que el usuario esté autenticado y posea el permiso requerido
    (o sea superusuario). Emite mensajes genéricos sin enumerar códigos.
    """
    permiso_requerido: str = ""
    message = _MENSAJE_GENERICO_DENEGADO

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if not self.permiso_requerido:
            return True

        # django has_perm espera formato 'app_label.codename'
        permiso_calificado = (
            self.permiso_requerido
            if "." in self.permiso_requerido
            else f"permisos.{self.permiso_requerido}"
        )

        tiene_permiso = request.user.has_perm(permiso_calificado)
        if not tiene_permiso:
            logger.info(
                "[AUTZ] Permiso denegado usuario=%s (%s) requerido=%s metodo=%s ruta=%s",
                getattr(request.user, "username", "?"),
                getattr(request.user, "id", "?"),
                self.permiso_requerido,
                request.method,
                request.path,
            )
            return False

        return True


def requiere_permiso(permiso: str) -> Type[BasePermission]:
    """
    Genera dinámicamente una clase de BasePermission atada al permiso especificado.
    """
    class _GuardPermisoEspecifico(PermisoRequerido):
        permiso_requerido = permiso

    _GuardPermisoEspecifico.__name__ = f"Permiso_{permiso}"
    return _GuardPermisoEspecifico


def permisos_por_metodo(mapa: dict[str, str]) -> Type[BasePermission]:
    """
    Genera una clase de BasePermission que inspecciona el método HTTP del request
    (GET, POST, PUT, PATCH, DELETE) y aplica el permiso correspondiente según el mapa.
    Si el método no está en el mapa, deniega el acceso por seguridad (deny-by-default).
    """
    class _GuardPorMetodo(BasePermission):
        message = _MENSAJE_GENERICO_DENEGADO

        def has_permission(self, request: Request, view: APIView) -> bool:
            if not request.user or not request.user.is_authenticated:
                return False

            if request.user.is_superuser:
                return True

            metodo = (request.method or "").upper()
            if metodo not in mapa:
                logger.warning(
                    "[AUTZ] Método HTTP %s no mapeado en permisos_por_metodo para vista %s. Denegado por defecto.",
                    metodo,
                    view.__class__.__name__,
                )
                return False

            permiso = mapa[metodo]
            if getattr(request, "_actividad_context", None) and metodo == "GET":
                from apps.permisos.codigos import Permisos
                if permiso == Permisos.SISTEMAS_VER:
                    return True
            permiso_calificado = permiso if "." in permiso else f"permisos.{permiso}"

            tiene_permiso = request.user.has_perm(permiso_calificado)
            if not tiene_permiso:
                logger.info(
                    "[AUTZ] Permiso denegado usuario=%s (%s) requerido=%s metodo=%s ruta=%s",
                    getattr(request.user, "username", "?"),
                    getattr(request.user, "id", "?"),
                    permiso,
                    metodo,
                    request.path,
                )
                return False

            return True

    _GuardPorMetodo.__name__ = "PermisosPorMetodoGuard"
    return _GuardPorMetodo
