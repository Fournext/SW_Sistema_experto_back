from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permisos.codigos import CATALOGO, Permisos
from apps.permisos.guards import requiere_permiso, permisos_por_metodo
from compartido.respuestas.respuesta_api import RespuestaAPI
from .models import RegistroAcceso
from .serializers import (
    PermisoSerializer,
    RegistroAccesoSerializer,
    ResetPasswordSerializer,
    RolCreateUpdateSerializer,
    RolSerializer,
    UsuarioCreateSerializer,
    UsuarioDetailSerializer,
    UsuarioListSerializer,
    UsuarioUpdateSerializer,
)
from .services import CentralService

Usuario = get_user_model()


class ResumenCentralAPIView(APIView):
    permission_classes = [requiere_permiso(Permisos.CENTRAL_ACCEDER)]

    def get(self, request):
        total_usuarios = Usuario.objects.count()
        usuarios_activos = Usuario.objects.filter(is_active=True).count()
        total_roles = Group.objects.count()
        sesiones_activas = len(CentralService.listar_sesiones_activas())
        total_accesos = RegistroAcceso.objects.count()

        ultimos_qs = RegistroAcceso.objects.select_related("usuario")[:10]
        ultimos_accesos_serializer = RegistroAccesoSerializer(ultimos_qs, many=True).data

        accesos_recientes = []
        for a in ultimos_accesos_serializer:
            accesos_recientes.append({
                "id": a["id"],
                "usuario": a["usuario"],
                "evento": a.get("evento_display") or a["evento"],
                "ip": a.get("ip") or "127.0.0.1",
                "fecha": a["fecha"],
                "resultado": a["resultado"],
            })

        data = {
            "usuarios_activos": usuarios_activos,
            "roles": total_roles,
            "sesiones_activas": sesiones_activas,
            "total_accesos": total_accesos,
            "accesos_recientes": accesos_recientes,
            "metricas": {
                "total_usuarios": total_usuarios,
                "usuarios_activos": usuarios_activos,
                "total_roles": total_roles,
                "sesiones_activas": sesiones_activas,
                "total_accesos": total_accesos,
            },
            "ultimos_accesos": ultimos_accesos_serializer,
        }
        return RespuestaAPI.exito(data=data)


class UsuarioListCreateAPIView(APIView):
    permission_classes = [
        permisos_por_metodo({
            "GET": Permisos.CENTRAL_USUARIOS_VER,
            "POST": Permisos.CENTRAL_USUARIOS_CREAR,
        })
    ]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        activo = request.query_params.get("activo")
        rol = request.query_params.get("rol")

        qs = Usuario.objects.prefetch_related("groups").order_by("-date_joined")
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(email__icontains=q)
                | Q(nombre_completo__icontains=q)
            )
        if activo is not None:
            if activo.lower() in ("true", "1"):
                qs = qs.filter(is_active=True)
            elif activo.lower() in ("false", "0"):
                qs = qs.filter(is_active=False)
        if rol:
            qs = qs.filter(groups__name=rol)

        serializer = UsuarioListSerializer(qs, many=True)
        return RespuestaAPI.exito(data=serializer.data)

    def post(self, request):
        serializer = UsuarioCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return RespuestaAPI.error(
                mensaje="Datos de usuario inválidos",
                errores=serializer.errors,
                codigo_estado=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        roles_solicitados = data.get("roles", [])

        # Soportar roles tanto si son IDs (int) como si son nombres (str)
        grupos_qs = Group.objects.none()
        if roles_solicitados:
            ids = [r for r in roles_solicitados if isinstance(r, int) or (isinstance(r, str) and str(r).isdigit())]
            nombres = [r for r in roles_solicitados if isinstance(r, str) and not str(r).isdigit()]
            grupos_qs = Group.objects.filter(Q(id__in=ids) | Q(name__in=nombres))

        # Validación anti-escalada
        permisos_roles = Permission.objects.filter(
            group__in=grupos_qs
        ).values_list("codename", flat=True)
        if not CentralService.validar_antiescalada(request.user, list(permisos_roles)):
            return RespuestaAPI.error(
                mensaje="No tiene autorización para asignar roles que contengan permisos superiores a los suyos.",
                codigo_estado=status.HTTP_403_FORBIDDEN,
            )

        nombre_final = data.get("nombre") or data.get("nombre_completo", "")
        usuario = Usuario.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            nombre_completo=nombre_final,
            is_active=data.get("is_active", True),
        )

        if grupos_qs.exists():
            usuario.groups.set(grupos_qs)

        return RespuestaAPI.exito(
            data=UsuarioDetailSerializer(usuario).data,
            mensaje="Usuario creado exitosamente.",
            codigo_estado=status.HTTP_201_CREATED,
        )


class UsuarioDetailAPIView(APIView):
    permission_classes = [
        permisos_por_metodo({
            "GET": Permisos.CENTRAL_USUARIOS_VER,
            "PUT": Permisos.CENTRAL_USUARIOS_EDITAR,
            "PATCH": Permisos.CENTRAL_USUARIOS_EDITAR,
        })
    ]

    def get(self, request, id: int):
        usuario = get_object_or_404(Usuario, id=id)
        return RespuestaAPI.exito(data=UsuarioDetailSerializer(usuario).data)

    def put(self, request, id: int):
        return self._actualizar(request, id, partial=False)

    def patch(self, request, id: int):
        return self._actualizar(request, id, partial=True)

    def _actualizar(self, request, id: int, partial: bool):
        usuario = get_object_or_404(Usuario, id=id)

        # Solo un superusuario puede editar a otro superusuario
        if usuario.is_superuser and not request.user.is_superuser:
            return RespuestaAPI.error(
                mensaje="Solo un superusuario puede modificar a otro superusuario.",
                codigo_estado=status.HTTP_403_FORBIDDEN,
            )

        serializer = UsuarioUpdateSerializer(
            data=request.data,
            context={"user_id": usuario.id},
            partial=partial,
        )
        if not serializer.is_valid():
            return RespuestaAPI.error(
                mensaje="Datos de actualización inválidos.",
                errores=serializer.errors,
                codigo_estado=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        if "roles" in data:
            roles_solicitados = data["roles"]
            ids = [r for r in roles_solicitados if isinstance(r, int) or (isinstance(r, str) and str(r).isdigit())]
            nombres = [r for r in roles_solicitados if isinstance(r, str) and not str(r).isdigit()]
            grupos_qs = Group.objects.filter(Q(id__in=ids) | Q(name__in=nombres))

            permisos_roles = Permission.objects.filter(
                group__in=grupos_qs
            ).values_list("codename", flat=True)
            if not CentralService.validar_antiescalada(request.user, list(permisos_roles)):
                return RespuestaAPI.error(
                    mensaje="No puede asignar roles con permisos que no posee.",
                    codigo_estado=status.HTTP_403_FORBIDDEN,
                )
            usuario.groups.set(grupos_qs)

        nombre_ingresado = data.get("nombre") or data.get("nombre_completo")
        if nombre_ingresado is not None:
            usuario.nombre_completo = nombre_ingresado
        if "email" in data:
            usuario.email = data["email"]
        if "telefono" in data:
            usuario.telefono = data["telefono"]
        if "biografia" in data:
            usuario.biografia = data["biografia"]
        if "is_active" in data:
            if not data["is_active"] and usuario.id == request.user.id:
                return RespuestaAPI.error(
                    mensaje="No puedes desactivar tu propia cuenta de usuario.",
                    codigo_estado=status.HTTP_400_BAD_REQUEST,
                )
            if not data["is_active"] and CentralService.es_ultimo_administrador(usuario.id):
                return RespuestaAPI.error(
                    mensaje="No se puede desactivar al único administrador activo del sistema.",
                    codigo_estado=status.HTTP_400_BAD_REQUEST,
                )
            usuario.is_active = data["is_active"]

        usuario.save()
        return RespuestaAPI.exito(
            data=UsuarioDetailSerializer(usuario).data,
            mensaje="Usuario actualizado correctamente.",
        )


class UsuarioActivarDesactivarAPIView(APIView):
    permission_classes = [requiere_permiso(Permisos.CENTRAL_USUARIOS_DESACTIVAR)]

    def post(self, request, id: int, accion: str):
        usuario = get_object_or_404(Usuario, id=id)

        if accion == "desactivar":
            if usuario.id == request.user.id:
                return RespuestaAPI.error(
                    mensaje="No puedes desactivar tu propia cuenta.",
                    codigo_estado=status.HTTP_400_BAD_REQUEST,
                )
            if CentralService.es_ultimo_administrador(usuario.id):
                return RespuestaAPI.error(
                    mensaje="No se puede desactivar al único administrador activo del sistema.",
                    codigo_estado=status.HTTP_400_BAD_REQUEST,
                )
            usuario.is_active = False
            usuario.save()
            CentralService.revocar_todas_sesiones_usuario(usuario.id)
            return RespuestaAPI.exito(mensaje="Usuario desactivado exitosamente.")

        elif accion == "activar":
            usuario.is_active = True
            usuario.save()
            return RespuestaAPI.exito(mensaje="Usuario activado exitosamente.")

        return RespuestaAPI.error(
            mensaje="Acción inválida. Use 'activar' o 'desactivar'.",
            codigo_estado=status.HTTP_400_BAD_REQUEST,
        )


class UsuarioResetPasswordAPIView(APIView):
    permission_classes = [requiere_permiso(Permisos.CENTRAL_USUARIOS_EDITAR)]

    def post(self, request, id: int):
        usuario = get_object_or_404(Usuario, id=id)
        if usuario.is_superuser and not request.user.is_superuser:
            return RespuestaAPI.error(
                mensaje="Solo un superusuario puede restablecer la clave de otro superusuario.",
                codigo_estado=status.HTTP_403_FORBIDDEN,
            )

        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return RespuestaAPI.error(
                mensaje="Contraseña inválida.",
                errores=serializer.errors,
                codigo_estado=status.HTTP_400_BAD_REQUEST,
            )

        nueva_clave = serializer.validated_data["password"]
        usuario.set_password(nueva_clave)
        usuario.save()

        # Invalida sesiones activas para exigir reingreso
        CentralService.revocar_todas_sesiones_usuario(usuario.id)

        return RespuestaAPI.exito(mensaje="Contraseña actualizada exitosamente.")


class RolListCreateAPIView(APIView):
    permission_classes = [
        permisos_por_metodo({
            "GET": Permisos.CENTRAL_ROLES_VER,
            "POST": Permisos.CENTRAL_ROLES_CREAR,
        })
    ]

    def get(self, request):
        roles = Group.objects.prefetch_related("permissions", "user_set").all().order_by("name")
        serializer = RolSerializer(roles, many=True)
        return RespuestaAPI.exito(data=serializer.data)

    def post(self, request):
        serializer = RolCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return RespuestaAPI.error(
                mensaje="Datos de rol inválidos.",
                errores=serializer.errors,
                codigo_estado=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        codigos_permisos = data.get("permisos", [])

        if not CentralService.validar_antiescalada(request.user, codigos_permisos):
            return RespuestaAPI.error(
                mensaje="No tiene permisos para asignar privilegios superiores a los propios.",
                codigo_estado=status.HTTP_403_FORBIDDEN,
            )

        grupo = Group.objects.create(name=data["name"])
        if codigos_permisos:
            permisos_qs = Permission.objects.filter(codename__in=codigos_permisos)
            grupo.permissions.set(permisos_qs)

        return RespuestaAPI.exito(
            data=RolSerializer(grupo).data,
            mensaje="Rol creado exitosamente.",
            codigo_estado=status.HTTP_201_CREATED,
        )


class RolDetailAPIView(APIView):
    permission_classes = [
        permisos_por_metodo({
            "GET": Permisos.CENTRAL_ROLES_VER,
            "PUT": Permisos.CENTRAL_ROLES_EDITAR,
            "PATCH": Permisos.CENTRAL_ROLES_EDITAR,
            "DELETE": Permisos.CENTRAL_ROLES_ELIMINAR,
        })
    ]

    def get(self, request, id: int):
        grupo = get_object_or_404(Group, id=id)
        return RespuestaAPI.exito(data=RolSerializer(grupo).data)

    def put(self, request, id: int):
        return self._actualizar(request, id)

    def patch(self, request, id: int):
        return self._actualizar(request, id)

    def _actualizar(self, request, id: int):
        grupo = get_object_or_404(Group, id=id)
        serializer = RolCreateUpdateSerializer(
            data=request.data,
            context={"rol_id": grupo.id},
        )
        if not serializer.is_valid():
            return RespuestaAPI.error(
                mensaje="Datos de rol inválidos.",
                errores=serializer.errors,
                codigo_estado=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        codigos_permisos = data.get("permisos", [])

        if not CentralService.validar_antiescalada(request.user, codigos_permisos):
            return RespuestaAPI.error(
                mensaje="No tiene permiso para otorgar permisos superiores a los suyos.",
                codigo_estado=status.HTTP_403_FORBIDDEN,
            )

        grupo.name = data["name"]
        grupo.save()

        permisos_qs = Permission.objects.filter(codename__in=codigos_permisos)
        grupo.permissions.set(permisos_qs)

        return RespuestaAPI.exito(
            data=RolSerializer(grupo).data,
            mensaje="Rol actualizado exitosamente.",
        )

    def delete(self, request, id: int):
        grupo = get_object_or_404(Group, id=id)
        usuarios_asignados = grupo.user_set.count()
        if usuarios_asignados > 0:
            return RespuestaAPI.error(
                mensaje=f"No se puede eliminar el rol '{grupo.name}' porque tiene {usuarios_asignados} usuario(s) asignado(s).",
                codigo_estado=status.HTTP_409_CONFLICT,
            )

        grupo.delete()
        return RespuestaAPI.exito(mensaje=f"Rol '{grupo.name}' eliminado exitosamente.")


class PermisoCatalogoListAPIView(APIView):
    permission_classes = [requiere_permiso(Permisos.CENTRAL_PERMISOS_VER)]

    def get(self, request):
        recurso = request.query_params.get("recurso")
        q = request.query_params.get("q", "").strip().lower()

        catalogo = list(CATALOGO)
        if recurso:
            catalogo = [p for p in catalogo if p.recurso == recurso]
        if q:
            catalogo = [
                p for p in catalogo
                if q in p.codigo.lower() or q in p.nombre.lower() or q in p.descripcion.lower()
            ]

        serializer = PermisoSerializer(catalogo, many=True)
        return RespuestaAPI.exito(data=serializer.data)


class SesionListAPIView(APIView):
    permission_classes = [requiere_permiso(Permisos.CENTRAL_SESIONES_VER)]

    def get(self, request):
        sesiones = CentralService.listar_sesiones_activas()
        return RespuestaAPI.exito(data=sesiones)


class SesionRevocarAPIView(APIView):
    permission_classes = [requiere_permiso(Permisos.CENTRAL_SESIONES_REVOCAR)]

    def delete(self, request, session_key: str):
        return self._revocar(session_key)

    def post(self, request, session_key: str):
        return self._revocar(session_key)

    def _revocar(self, session_key: str):
        exito = CentralService.revocar_sesion(session_key)
        if exito:
            return RespuestaAPI.exito(mensaje="Sesión revocada exitosamente.")
        return RespuestaAPI.error(
            mensaje="No se encontró una sesión activa con la clave proporcionada.",
            codigo_estado=status.HTTP_404_NOT_FOUND,
        )


class BitacoraListAPIView(APIView):
    permission_classes = [requiere_permiso(Permisos.CENTRAL_BITACORA_VER)]

    def get(self, request):
        evento = request.query_params.get("evento")
        username = request.query_params.get("username")

        qs = RegistroAcceso.objects.select_related("usuario").order_by("-fecha")
        if evento:
            qs = qs.filter(evento=evento)
        if username:
            qs = qs.filter(username_ingresado__icontains=username)

        serializer = RegistroAccesoSerializer(qs[:100], many=True)
        return RespuestaAPI.exito(data=serializer.data)
