import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import RequestFactory
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permisos.codigos import CATALOGO, GRUPOS_CONFIG, Permisos, prefijo, slug_sistema
from apps.permisos.guards import permisos_por_metodo, requiere_permiso
from apps.permisos.services import PermisoService

Usuario = get_user_model()


def test_catalogo_y_constantes_coherentes():
    """El catálogo debe tener exactamente 56 permisos atómicos sin duplicados."""
    codigos = [d.codigo for d in CATALOGO]
    assert len(codigos) == 56
    assert len(set(codigos)) == 56
    assert len(Permisos.TODOS) == 56
    assert Permisos.TODOS == frozenset(codigos)


def test_prefijo_slug_sistema():
    """El prefijo debe derivarse del slug con guiones bajos y '_' al final."""
    assert slug_sistema() == "sistema-experto"
    assert prefijo() == "sistema_experto_"
    assert Permisos.SISTEMAS_VER == "sistema_experto_sistemas_ver"


def test_grupos_configuracion_coherente():
    """Todos los permisos asignados a grupos deben existir en el catálogo."""
    todos = Permisos.TODOS
    for nombre_grupo, lista_permisos in GRUPOS_CONFIG.items():
        for p in lista_permisos:
            assert p in todos, f"Permiso {p} en grupo {nombre_grupo} no existe en CATALOGO"

    # Verificar que el grupo Estudiante tenga exactamente los 6 permisos definidos
    assert len(GRUPOS_CONFIG["Estudiante"]) == 6
    assert Permisos.ACTIVIDADES_RESOLVER in GRUPOS_CONFIG["Estudiante"]
    assert Permisos.ENTREGAS_ENVIAR in GRUPOS_CONFIG["Estudiante"]
    assert Permisos.CENTRAL_ACCEDER not in GRUPOS_CONFIG["Estudiante"]
    assert Permisos.CENTRAL_ACCEDER not in GRUPOS_CONFIG["Docente"]
    assert Permisos.CENTRAL_ACCEDER in GRUPOS_CONFIG["Administrador central"]


@pytest.mark.django_db
def test_guards_permiso_requerido(usuario_docente, usuario_estudiante, superusuario):
    """Verifica que requiere_permiso permita o deniegue según los permisos asignados."""
    from rest_framework.test import APIRequestFactory, force_authenticate

    class DummyView(APIView):
        permission_classes = [requiere_permiso(Permisos.SISTEMAS_CREAR)]
        def post(self, request):
            return Response({"ok": True})

    factory = APIRequestFactory()
    view = DummyView.as_view()

    # 1. Anónimo -> 401
    req_anon = factory.post("/test/")
    resp_anon = view(req_anon)
    assert resp_anon.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Estudiante (no tiene sistemas_crear) -> 403
    req_est = factory.post("/test/")
    force_authenticate(req_est, user=usuario_estudiante)
    resp_est = view(req_est)
    assert resp_est.status_code == status.HTTP_403_FORBIDDEN

    # 3. Docente (tiene sistemas_crear) -> 200
    req_doc = factory.post("/test/")
    force_authenticate(req_doc, user=usuario_docente)
    resp_doc = view(req_doc)
    assert resp_doc.status_code == status.HTTP_200_OK

    # 4. Superusuario -> 200
    req_root = factory.post("/test/")
    force_authenticate(req_root, user=superusuario)
    resp_root = view(req_root)
    assert resp_root.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_guards_permisos_por_metodo(usuario_docente, usuario_estudiante):
    """Verifica permisos_por_metodo con deny-by-default para métodos no declarados."""
    from rest_framework.test import APIRequestFactory, force_authenticate

    class DummyCrudView(APIView):
        permission_classes = [
            permisos_por_metodo({
                "GET": Permisos.SISTEMAS_VER,
                "POST": Permisos.SISTEMAS_CREAR,
            })
        ]
        def get(self, request): return Response({"accion": "get"})
        def post(self, request): return Response({"accion": "post"})
        def delete(self, request): return Response({"accion": "delete"})

    factory = APIRequestFactory()
    view = DummyCrudView.as_view()

    # GET para estudiante (tiene sistemas_ver) -> 200
    req_get = factory.get("/test/")
    force_authenticate(req_get, user=usuario_estudiante)
    assert view(req_get).status_code == status.HTTP_200_OK

    # POST para estudiante (no tiene sistemas_crear) -> 403
    req_post = factory.post("/test/")
    force_authenticate(req_post, user=usuario_estudiante)
    assert view(req_post).status_code == status.HTTP_403_FORBIDDEN

    # DELETE para docente (DELETE no está en el mapa -> deny-by-default) -> 403
    req_del = factory.delete("/test/")
    force_authenticate(req_del, user=usuario_docente)
    assert view(req_del).status_code == status.HTTP_403_FORBIDDEN
