import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from apps.central.models import RegistroAcceso

Usuario = get_user_model()


@pytest.mark.django_db
def test_login_exitoso_y_emision_jwt(api_client_anonimo, usuario_docente):
    """Prueba que el login con credenciales válidas entregue tokens JWT y datos de usuario."""
    url = reverse("autenticacion:login")
    resp = api_client_anonimo.post(
        url,
        data={"username": "test_docente", "password": "Password123*"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.data["data"]
    assert "access" in data
    assert "refresh" in data
    assert data["user"]["username"] == "test_docente"
    assert "Docente" in data["user"]["roles"]
    assert not data["user"]["es_admin_central"]

    # Verificar registro en bitácora
    acceso = RegistroAcceso.objects.filter(username_ingresado="test_docente").first()
    assert acceso is not None
    assert acceso.evento == "login_ok"


@pytest.mark.django_db
def test_login_credenciales_invalidas_registra_bitacora(api_client_anonimo):
    """Credenciales incorrectas devuelven 401 y quedan registradas en bitácora."""
    url = reverse("autenticacion:login")
    resp = api_client_anonimo.post(
        url,
        data={"username": "intruso", "password": "wrong_password"},
        format="json",
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.data["message"] == "Usuario o contraseña incorrectos."

    acceso = RegistroAcceso.objects.filter(username_ingresado="intruso").first()
    assert acceso is not None
    assert acceso.evento == "login_fallido"


@pytest.mark.django_db
def test_autoregistro_estudiante_exitoso(api_client_anonimo):
    """Los estudiantes pueden autoregistrarse y reciben automáticamente el rol Estudiante."""
    url = reverse("autenticacion:registro_estudiante")
    payload = {
        "username": "nuevo_alumno",
        "email": "alumno@uagrm.edu.bo",
        "nombre_completo": "Juan Perez Alumno",
        "password": "Password123*",
        "confirmar_password": "Password123*",
    }
    resp = api_client_anonimo.post(url, data=payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.data["data"]
    assert "access" in data
    assert data["user"]["username"] == "nuevo_alumno"
    assert "Estudiante" in data["user"]["roles"]

    # Verificar en BD
    usuario = Usuario.objects.get(username="nuevo_alumno")
    assert usuario.es_estudiante
    assert not usuario.es_docente


@pytest.mark.django_db
def test_autoregistro_estudiante_validaciones(api_client_anonimo, usuario_estudiante):
    """Valida duplicidad de username o email y coincidencia de contraseña."""
    url = reverse("autenticacion:registro_estudiante")

    # Contraseñas no coinciden
    resp1 = api_client_anonimo.post(
        url,
        data={
            "username": "alumno2",
            "email": "alumno2@test.bo",
            "nombre_completo": "Test",
            "password": "Password123*",
            "confirmar_password": "DifferentPassword*",
        },
        format="json",
    )
    assert resp1.status_code == status.HTTP_400_BAD_REQUEST

    # Email o username ya en uso
    resp2 = api_client_anonimo.post(
        url,
        data={
            "username": "test_estudiante",
            "email": "otro@test.bo",
            "nombre_completo": "Test",
            "password": "Password123*",
            "confirmar_password": "Password123*",
        },
        format="json",
    )
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_endpoint_yo(api_client, usuario_docente):
    """El endpoint /auth/yo/ retorna los datos y permisos del usuario autenticado."""
    url = reverse("autenticacion:yo")
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["data"]["username"] == usuario_docente.username
    assert len(resp.data["data"]["permisos"]) > 0


@pytest.mark.django_db
def test_logout(api_client, usuario_docente):
    """El logout finaliza sesión y registra en bitácora."""
    url = reverse("autenticacion:logout")
    resp = api_client.post(url, data={}, format="json")
    assert resp.status_code == status.HTTP_200_OK

    acceso = RegistroAcceso.objects.filter(usuario=usuario_docente, evento="logout").first()
    assert acceso is not None
