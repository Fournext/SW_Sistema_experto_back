import logging
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone
from apps.permisos.codigos import Permisos
from .models import RegistroAcceso

logger = logging.getLogger(__name__)
Usuario = get_user_model()


def obtener_ip(request) -> str | None:
    """Extrae la IP real del cliente considerando proxies inversos estándar."""
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class CentralService:
    @staticmethod
    def registrar_evento(
        evento: str,
        username_ingresado: str,
        request=None,
        usuario=None,
        detalles: dict | None = None,
    ) -> RegistroAcceso:
        """Registra un evento de seguridad en la bitácora sin persistir contraseñas."""
        ip = obtener_ip(request) if request else None
        user_agent = ""
        if request and hasattr(request, "META"):
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:250]

        return RegistroAcceso.objects.create(
            usuario=usuario,
            username_ingresado=username_ingresado,
            evento=evento,
            ip=ip,
            user_agent=user_agent,
            detalles=detalles or {},
        )

    @staticmethod
    def validar_antiescalada(actor, permisos_a_asignar: list[str]) -> bool:
        """
        Garantiza que ningún administrador pueda asignar permisos que él mismo no posea.
        Los superusuarios están exentos.
        """
        if not actor or not actor.is_authenticated:
            return False
        if actor.is_superuser:
            return True

        permisos_actor = set(actor.obtener_permisos_lista())
        faltantes = set(permisos_a_asignar) - permisos_actor
        if faltantes:
            logger.warning(
                "[ANTI-ESCALADA] Usuario %s intentó asignar permisos que no posee: %s",
                actor.username,
                faltantes,
            )
            return False
        return True

    @staticmethod
    def es_ultimo_administrador(usuario_id: int) -> bool:
        """
        Comprueba si el usuario indicado es el único administrador activo del sistema
        (superusuario o con permiso central_acceder).
        """
        permiso_admin = f"permisos.{Permisos.CENTRAL_ACCEDER}"
        admins_activos = Usuario.objects.filter(is_active=True).filter(
            models_Q_admin(permiso_admin)
        ).distinct()

        # Si sólo hay un admin y coincide con el usuario_id consultado
        ids = list(admins_activos.values_list("id", flat=True))
        return len(ids) == 1 and ids[0] == usuario_id

    @staticmethod
    def listar_sesiones_activas() -> list[dict]:
        """
        Devuelve información estructurada de las sesiones activas en el backend.
        """
        ahora = timezone.now()
        sesiones = Session.objects.filter(expire_date__gt=ahora).order_by("-expire_date")
        lista = []

        for s in sesiones:
            data = s.get_decoded()
            user_id = data.get("_auth_user_id")
            usuario_info = None
            username = "Desconocido"
            if user_id:
                u = Usuario.objects.filter(id=user_id).first()
                if u:
                    username = u.username
                    usuario_info = {
                        "id": u.id,
                        "username": u.username,
                        "nombre_completo": u.nombre_para_mostrar,
                        "email": u.email,
                    }

            lista.append({
                "id": s.session_key,
                "session_key": s.session_key,
                "expire_date": s.expire_date.isoformat(),
                "usuario": username,
                "usuario_detalle": usuario_info,
                "ip": data.get("ip", "127.0.0.1"),
                "fecha_inicio": data.get("fecha_inicio", s.expire_date.isoformat()),
                "ultimo_acceso": data.get("ultimo_acceso", s.expire_date.isoformat()),
                "activa": True,
            })
        return lista

    @staticmethod
    def revocar_sesion(session_key: str) -> bool:
        """Elimina una sesión activa por su clave."""
        eliminados, _ = Session.objects.filter(session_key=session_key).delete()
        return eliminados > 0

    @staticmethod
    def revocar_todas_sesiones_usuario(usuario_id: int) -> int:
        """Invalida todas las sesiones activas asociadas a un ID de usuario."""
        ahora = timezone.now()
        sesiones = Session.objects.filter(expire_date__gt=ahora)
        claves_a_borrar = []
        for s in sesiones:
            data = s.get_decoded()
            if str(data.get("_auth_user_id")) == str(usuario_id):
                claves_a_borrar.append(s.session_key)

        if claves_a_borrar:
            eliminados, _ = Session.objects.filter(session_key__in=claves_a_borrar).delete()
            return eliminados
        return 0


def models_Q_admin(permiso_calificado: str):
    from django.db.models import Q
    return Q(is_superuser=True) | Q(user_permissions__codename=permiso_calificado.split(".")[1]) | Q(groups__permissions__codename=permiso_calificado.split(".")[1])
