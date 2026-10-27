from django.urls import path
from .views import (
    BitacoraListAPIView,
    PermisoCatalogoListAPIView,
    ResumenCentralAPIView,
    RolDetailAPIView,
    RolListCreateAPIView,
    SesionListAPIView,
    SesionRevocarAPIView,
    UsuarioActivarDesactivarAPIView,
    UsuarioDetailAPIView,
    UsuarioListCreateAPIView,
    UsuarioResetPasswordAPIView,
)

app_name = "central"

urlpatterns = [
    # Resumen / Panel
    path("central/panel/", ResumenCentralAPIView.as_view(), name="panel"),
    path("central/resumen/", ResumenCentralAPIView.as_view(), name="resumen"),

    # Usuarios
    path("central/usuarios/", UsuarioListCreateAPIView.as_view(), name="usuarios_list_create"),
    path("central/usuarios/<int:id>/", UsuarioDetailAPIView.as_view(), name="usuarios_detail"),
    path("central/usuarios/<int:id>/<str:accion>/", UsuarioActivarDesactivarAPIView.as_view(), name="usuarios_activar_desactivar"),
    path("central/usuarios/<int:id>/reset-password/", UsuarioResetPasswordAPIView.as_view(), name="usuarios_reset_password"),
    path("central/usuarios/<int:id>/restablecer-password/", UsuarioResetPasswordAPIView.as_view(), name="usuarios_restablecer_password"),

    # Roles (Grupos)
    path("central/roles/", RolListCreateAPIView.as_view(), name="roles_list_create"),
    path("central/roles/<int:id>/", RolDetailAPIView.as_view(), name="roles_detail"),

    # Catálogo de permisos
    path("central/permisos/", PermisoCatalogoListAPIView.as_view(), name="permisos_catalogo"),

    # Sesiones activas
    path("central/sesiones/", SesionListAPIView.as_view(), name="sesiones_list"),
    path("central/sesiones/<str:session_key>/", SesionRevocarAPIView.as_view(), name="sesion_revocar"),
    path("central/sesiones/<str:session_key>/revocar/", SesionRevocarAPIView.as_view(), name="sesion_revocar_post"),

    # Bitácora
    path("central/bitacora/", BitacoraListAPIView.as_view(), name="bitacora_list"),
]
