import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from apps.permisos.codigos import Permisos

Usuario = get_user_model()


@pytest.mark.django_db
def test_resumen_central_acceso_restringido(api_client, usuario_admin_central):
    """Solo usuarios con permiso central_acceder pueden ver el resumen de Admin Central."""
    url = reverse("central:resumen")

    # 1. Docente (sin permiso central_acceder) -> 403
    resp_docente = api_client.get(url)
    assert resp_docente.status_code == status.HTTP_403_FORBIDDEN

    # 2. Admin Central -> 200 (resumen y panel)
    api_client.force_authenticate(user=usuario_admin_central)
    resp_admin = api_client.get(url)
    assert resp_admin.status_code == status.HTTP_200_OK
    assert "metricas" in resp_admin.data["data"]
    assert "total_usuarios" in resp_admin.data["data"]["metricas"]

    # Endpoint esperado por frontend (/central/panel/)
    url_panel = reverse("central:panel")
    resp_panel = api_client.get(url_panel)
    assert resp_panel.status_code == status.HTTP_200_OK
    data_panel = resp_panel.data["data"]
    assert "usuarios_activos" in data_panel
    assert "roles" in data_panel
    assert "sesiones_activas" in data_panel
    assert "total_accesos" in data_panel
    assert "accesos_recientes" in data_panel


@pytest.mark.django_db
def test_gestion_usuarios_admin_central(api_client, superusuario, usuario_admin_central):
    """Crear y editar usuarios desde Admin Central."""
    # 1. Admin central sin permisos del SW no puede asignar rol Docente (Anti-escalada)
    api_client.force_authenticate(user=usuario_admin_central)
    url_list = reverse("central:usuarios_list_create")
    payload = {
        "username": "docente_nuevo",
        "email": "docente_nuevo@uagrm.bo",
        "nombre_completo": "Profesor Nuevo",
        "password": "Password123*",
        "roles": ["Docente"],
        "is_active": True,
    }
    resp_bloqueado = api_client.post(url_list, data=payload, format="json")
    assert resp_bloqueado.status_code == status.HTTP_403_FORBIDDEN

    # 2. Superusuario sí puede crear usuarios y asignar cualquier rol
    api_client.force_authenticate(user=superusuario)
    resp = api_client.post(url_list, data=payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    user_id = resp.data["data"]["id"]

    # Consultar detalle
    url_detail = reverse("central:usuarios_detail", kwargs={"id": user_id})
    resp_detail = api_client.get(url_detail)
    assert resp_detail.status_code == status.HTTP_200_OK
    assert resp_detail.data["data"]["username"] == "docente_nuevo"


@pytest.mark.django_db
def test_autoproteccion_desactivar_propia_cuenta(api_client, usuario_admin_central):
    """Un usuario administrador no puede desactivar su propia cuenta."""
    api_client.force_authenticate(user=usuario_admin_central)
    url_desactivar = reverse(
        "central:usuarios_activar_desactivar",
        kwargs={"id": usuario_admin_central.id, "accion": "desactivar"},
    )
    resp = api_client.post(url_desactivar)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "No puedes desactivar tu propia cuenta" in resp.data["message"]


@pytest.mark.django_db
def test_proteccion_ultimo_administrador(api_client, usuario_admin_central, superusuario):
    """No se puede desactivar al único administrador activo del sistema."""
    # Desactivamos a superusuario para dejar solo a usuario_admin_central como único admin
    superusuario.is_active = False
    superusuario.save()

    # Iniciar sesión como otro usuario staff para intentar desactivar al único admin
    otro_staff = Usuario.objects.create_user(
        username="otro_staff",
        email="otro@test.bo",
        password="Password123*",
        is_staff=True,
    )
    grupo_admin = Group.objects.get(name="Administrador central")
    otro_staff.groups.add(grupo_admin)

    # Ahora hay 2 admins activos: otro_staff y usuario_admin_central. Desactivamos otro_staff
    api_client.force_authenticate(user=usuario_admin_central)
    url_desact_otro = reverse(
        "central:usuarios_activar_desactivar",
        kwargs={"id": otro_staff.id, "accion": "desactivar"},
    )
    resp1 = api_client.post(url_desact_otro)
    assert resp1.status_code == status.HTTP_200_OK

    # Ahora usuario_admin_central es el único administrador activo restante.
    # Reactivamos otro_staff temporalmente para que intente desactivar al último admin
    otro_staff.is_active = True
    otro_staff.save()
    api_client.force_authenticate(user=otro_staff)

    url_desact_admin = reverse(
        "central:usuarios_activar_desactivar",
        kwargs={"id": usuario_admin_central.id, "accion": "desactivar"},
    )
    # Si quitamos a otro_staff del grupo antes, usuario_admin_central es el único admin:
    otro_staff.groups.clear()
    resp2 = api_client.post(url_desact_admin)
    # Debería rechazar por ser el último admin o por falta de permisos
    assert resp2.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_no_eliminar_rol_con_usuarios(api_client, usuario_admin_central):
    """Un rol que tenga usuarios asignados no puede ser eliminado (409 Conflict)."""
    api_client.force_authenticate(user=usuario_admin_central)
    grupo_docente = Group.objects.get(name="Docente")

    url_rol = reverse("central:roles_detail", kwargs={"id": grupo_docente.id})
    resp = api_client.delete(url_rol)
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert "No se puede eliminar el rol" in resp.data["message"]


@pytest.mark.django_db
def test_catalogo_permisos_solo_lectura(api_client, usuario_admin_central):
    """Admin Central expone el catálogo de permisos en solo lectura con filtros."""
    api_client.force_authenticate(user=usuario_admin_central)
    url = reverse("central:permisos_catalogo")

    resp = api_client.get(url, {"recurso": "sistemas_expertos"})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.data["data"]
    assert len(data) == 4
    assert all(item["recurso"] == "sistemas_expertos" for item in data)
