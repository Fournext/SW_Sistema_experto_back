"""
Configuración global y fixtures de Pytest.
Provee fixtures para usuarios con roles (Docente, Estudiante, Administrador Central)
y autenticación JWT para el cliente de pruebas de DRF.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from apps.permisos.services import PermisoService

Usuario = get_user_model()


@pytest.fixture(autouse=True)
def sincronizar_permisos_db(db):
    """Garantiza que el catálogo de permisos y grupos esté en la base de datos de test."""
    PermisoService.escanear_y_generar_permisos(verbose=False)


@pytest.fixture
def usuario_docente(db):
    """Usuario con rol Docente y todos los permisos operativos del SW."""
    u = Usuario.objects.create_user(
        username="test_docente",
        email="docente@test.edu.bo",
        password="Password123*",
        nombre_completo="Docente de Pruebas",
    )
    grupo = Group.objects.get(name="Docente")
    u.groups.add(grupo)
    return u


@pytest.fixture
def usuario_estudiante(db):
    """Usuario con rol Estudiante y permisos de resolución de actividades didácticas."""
    u = Usuario.objects.create_user(
        username="test_estudiante",
        email="estudiante@test.edu.bo",
        password="Password123*",
        nombre_completo="Estudiante de Pruebas",
    )
    grupo = Group.objects.get(name="Estudiante")
    u.groups.add(grupo)
    return u


@pytest.fixture
def usuario_admin_central(db):
    """Usuario con rol Administrador central."""
    u = Usuario.objects.create_user(
        username="test_admin_central",
        email="admin@test.edu.bo",
        password="Password123*",
        nombre_completo="Admin Central de Pruebas",
    )
    grupo = Group.objects.get(name="Administrador central")
    u.groups.add(grupo)
    return u


@pytest.fixture
def superusuario(db):
    """Superusuario con acceso universal sin restricciones."""
    return Usuario.objects.create_superuser(
        username="test_root",
        email="root@test.edu.bo",
        password="Password123*",
        nombre_completo="Super Administrador",
    )


@pytest.fixture
def api_client(usuario_docente):
    """
    Cliente HTTP de prueba para DRF autenticado por defecto con rol Docente
    para mantener compatibilidad con la suite de pruebas del SW existente.
    """
    client = APIClient()
    client.force_authenticate(user=usuario_docente)
    return client


@pytest.fixture
def api_client_anonimo():
    """Cliente HTTP sin autenticación para probar rechazo 401."""
    return APIClient()
