import secrets
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.central.services import CentralService
from compartido.respuestas.respuesta_api import RespuestaAPI
from .serializers import (
    LoginSerializer,
    RegistroCorporativoStudioSerializer,
    RegistroEstudianteSerializer,
    UsuarioYoSerializer,
)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username_ingresado = request.data.get("username", "").strip()
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            CentralService.registrar_evento(
                evento="login_fallido",
                username_ingresado=username_ingresado,
                request=request,
                detalles={"motivo": serializer.errors},
            )
            return RespuestaAPI.error(
                mensaje="Usuario o contraseña incorrectos.",
                errores=serializer.errors,
                codigo_estado=status.HTTP_401_UNAUTHORIZED,
            )

        usuario = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(usuario)

        # Inyectar claims personalizados en el token
        refresh["username"] = usuario.username
        refresh["es_admin_central"] = usuario.es_admin_central

        CentralService.registrar_evento(
            evento="login_ok",
            username_ingresado=usuario.username,
            request=request,
            usuario=usuario,
        )

        user_data = UsuarioYoSerializer(usuario).data

        return RespuestaAPI.exito(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data,
            },
            mensaje="Inicio de sesión exitoso.",
        )


class RegistroEstudianteAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroEstudianteSerializer(data=request.data)
        if not serializer.is_valid():
            return RespuestaAPI.error(
                mensaje="Datos de registro inválidos.",
                errores=serializer.errors,
                codigo_estado=status.HTTP_400_BAD_REQUEST,
            )

        usuario = serializer.save()
        refresh = RefreshToken.for_user(usuario)
        refresh["username"] = usuario.username
        refresh["es_admin_central"] = False

        CentralService.registrar_evento(
            evento="registro",
            username_ingresado=usuario.username,
            request=request,
            usuario=usuario,
            detalles={"tipo": "autoregistro_estudiante"},
        )

        user_data = UsuarioYoSerializer(usuario).data

        return RespuestaAPI.exito(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data,
            },
            mensaje="Cuenta de estudiante creada exitosamente.",
            codigo_estado=status.HTTP_201_CREATED,
        )


class YoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UsuarioYoSerializer(request.user)
        return RespuestaAPI.exito(data=serializer.data)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        CentralService.registrar_evento(
            evento="logout",
            username_ingresado=request.user.username,
            request=request,
            usuario=request.user,
        )

        return RespuestaAPI.exito(mensaje="Sesión finalizada exitosamente.")


class RegistroCorporativoStudioAPIView(APIView):
    """
    Endpoint interno para provisionar o sincronizar usuarios desde la landing empresarial
    con rol Docente o Estudiante y devolver tokens JWT para SSO.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        service_key = request.headers.get("X-Studio-Service-Key", "")
        expected_key = getattr(settings, "STUDIO_SERVICE_KEY", "")
        if not expected_key or not secrets.compare_digest(service_key, expected_key):
            return RespuestaAPI.error(
                mensaje="Clave de servicio corporativo inválida.",
                codigo_estado=status.HTTP_403_FORBIDDEN,
            )

        serializer = RegistroCorporativoStudioSerializer(data=request.data)
        if not serializer.is_valid():
            return RespuestaAPI.error(
                mensaje="Datos inválidos para aprovisionamiento corporativo.",
                errores=serializer.errors,
                codigo_estado=status.HTTP_400_BAD_REQUEST,
            )

        usuario = serializer.create_or_sync()
        refresh = RefreshToken.for_user(usuario)
        refresh["username"] = usuario.username
        refresh["es_admin_central"] = usuario.es_admin_central

        CentralService.registrar_evento(
            evento="registro_corporativo",
            username_ingresado=usuario.username,
            request=request,
            usuario=usuario,
            detalles={"rol": serializer.validated_data["rol"]},
        )

        return RespuestaAPI.exito(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UsuarioYoSerializer(usuario).data,
            },
            mensaje="Usuario sincronizado en ExpertEdu Studio correctamente.",
            codigo_estado=status.HTTP_200_OK,
        )


class AceptarTerminosAPIView(APIView):
    """Registra la aceptación obligatoria de términos y condiciones al primer ingreso."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.data.get("aceptado", False):
            return RespuestaAPI.error(
                mensaje="Debe aceptar los términos y condiciones para continuar.",
                codigo_estado=status.HTTP_400_BAD_REQUEST,
            )

        usuario = request.user
        if not usuario.terminos_aceptados:
            usuario.terminos_aceptados = True
            usuario.terminos_aceptados_en = timezone.now()
            usuario.save(update_fields=["terminos_aceptados", "terminos_aceptados_en"])

        return RespuestaAPI.exito(
            data=UsuarioYoSerializer(usuario).data,
            mensaje="Términos y condiciones aceptados.",
        )
