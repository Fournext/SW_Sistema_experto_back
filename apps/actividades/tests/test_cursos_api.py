import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import path
from rest_framework.test import APIClient

from apps.actividades.cursos_api import (
    CursosListCreateAPIView, CursoDetailAPIView, CursoUnirseAPIView,
    CursoRegenerarInvitacionAPIView, CursoMiembrosAPIView, CursoMiembroDetailAPIView,
    matricula_activa,
)
from apps.actividades.models import CursoModel, MatriculaCursoModel, ActividadEducativaModel, AsignacionActividadModel
from apps.sistemas_expertos.models import SistemaExpertoModel


urlpatterns = [
    path("api/v1/cursos/", CursosListCreateAPIView.as_view()),
    path("api/v1/cursos/unirse/", CursoUnirseAPIView.as_view()),
    path("api/v1/cursos/<uuid:id>/", CursoDetailAPIView.as_view()),
    path("api/v1/cursos/<uuid:id>/invitacion/regenerar/", CursoRegenerarInvitacionAPIView.as_view()),
    path("api/v1/cursos/<uuid:id>/miembros/", CursoMiembrosAPIView.as_view()),
    path("api/v1/cursos/<uuid:id>/miembros/<int:estudiante_id>/", CursoMiembroDetailAPIView.as_view()),
]


@pytest.fixture(autouse=True)
def rutas_cursos(settings):
    # Aísla las vistas nuevas del cableado de rutas que integra el agente padre.
    settings.ROOT_URLCONF = __name__


def cliente(usuario):
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


@pytest.fixture
def segundo_docente(db):
    usuario = get_user_model().objects.create_user(username="otro_docente", password="Clave123*", email="otro@escuela.test")
    usuario.groups.add(Group.objects.get(name="Docente"))
    return usuario


@pytest.fixture
def otro_estudiante(db):
    usuario = get_user_model().objects.create_user(username="otro_estudiante", password="Clave123*", email="otro.est@escuela.test")
    usuario.groups.add(Group.objects.get(name="Estudiante"))
    return usuario


def crear_curso(client, codigo="SIS-101"):
    respuesta = client.post("/api/v1/cursos/", {"codigo": codigo, "nombre": "Sistemas Expertos", "descripcion": "Grupo académico"}, format="json")
    assert respuesta.status_code == 201, respuesta.content
    return respuesta.json()["data"]


@pytest.mark.django_db
def test_cursos_docente_propietario_otros_roles_y_creacion_no_matricula_automaticamente(
    usuario_docente, segundo_docente, usuario_estudiante, usuario_admin_central, superusuario,
):
    docente, otro, estudiante = cliente(usuario_docente), cliente(segundo_docente), cliente(usuario_estudiante)
    curso = crear_curso(docente)
    otro_curso = crear_curso(otro, "SIS-102")
    assert curso["codigo_ingreso"] != curso["codigo"]
    assert curso["token_ingreso"] in curso["enlace_invitacion"]
    assert curso["total_miembros"] == 0
    assert MatriculaCursoModel.objects.count() == 0
    assert [c["id"] for c in docente.get("/api/v1/cursos/").json()["data"]] == [curso["id"]]
    assert {c["id"] for c in cliente(superusuario).get("/api/v1/cursos/").json()["data"]} == {curso["id"], otro_curso["id"]}
    assert estudiante.get("/api/v1/cursos/").json()["data"] == []
    assert estudiante.post("/api/v1/cursos/", {"codigo": "INTRUSO", "nombre": "No"}, format="json").status_code == 403
    assert cliente(usuario_admin_central).get("/api/v1/cursos/").status_code == 403
    for metodo in [otro.get, otro.patch]:
        assert metodo(f"/api/v1/cursos/{curso['id']}/", {}).status_code == 404
    assert otro.post(f"/api/v1/cursos/{curso['id']}/invitacion/regenerar/", {}).status_code == 404
    assert docente.patch(f"/api/v1/cursos/{curso['id']}/", {"docente_id": segundo_docente.id, "nombre": "Nuevo nombre"}, format="json").status_code == 200
    assert CursoModel.objects.get(pk=curso["id"]).docente_id == usuario_docente.id


@pytest.mark.django_db
def test_ingreso_inmediato_idempotente_y_rotacion_revoca_codigo_y_token(usuario_docente, usuario_estudiante, otro_estudiante):
    docente, estudiante = cliente(usuario_docente), cliente(usuario_estudiante)
    curso = crear_curso(docente)
    assert APIClient().post("/api/v1/cursos/unirse/", {"codigo": curso["codigo_ingreso"]}, format="json").status_code == 401
    assert estudiante.post("/api/v1/cursos/unirse/", {"codigo": curso["codigo"]}, format="json").status_code == 404
    primera = estudiante.post("/api/v1/cursos/unirse/", {"codigo": curso["codigo_ingreso"].lower()}, format="json")
    assert primera.status_code == 201
    assert primera.json()["data"]["matricula_activa"] is True
    assert "token_ingreso" not in primera.json()["data"]
    assert "codigo_ingreso" not in primera.json()["data"]
    assert estudiante.post("/api/v1/cursos/unirse/", {"token": curso["token_ingreso"]}, format="json").status_code == 200
    assert MatriculaCursoModel.objects.count() == 1
    assert matricula_activa(curso["id"], usuario_estudiante)
    detalle = estudiante.get(f"/api/v1/cursos/{curso['id']}/").json()["data"]
    assert detalle["total_miembros"] == 1
    assert detalle["asignaciones"] == []
    assert "enlace_invitacion" not in detalle
    nueva = docente.post(f"/api/v1/cursos/{curso['id']}/invitacion/regenerar/", {}).json()["data"]
    assert nueva["codigo_ingreso"] not in (curso["codigo_ingreso"], curso["codigo"])
    assert nueva["token_ingreso"] != curso["token_ingreso"]
    otro = cliente(otro_estudiante)
    for credencial in [{"codigo": curso["codigo_ingreso"]}, {"token": curso["token_ingreso"]}]:
        assert otro.post("/api/v1/cursos/unirse/", credencial, format="json").status_code == 404
    assert otro.post("/api/v1/cursos/unirse/", {"token": nueva["token_ingreso"]}, format="json").status_code == 201
    assert MatriculaCursoModel.objects.count() == 2


@pytest.mark.django_db
def test_retirado_no_puede_reingresar_y_docente_debe_reactivar(usuario_docente, usuario_estudiante, segundo_docente):
    docente, estudiante = cliente(usuario_docente), cliente(usuario_estudiante)
    curso = crear_curso(docente)
    estudiante.post("/api/v1/cursos/unirse/", {"token": curso["token_ingreso"]}, format="json")
    url_miembro = f"/api/v1/cursos/{curso['id']}/miembros/{usuario_estudiante.id}/"
    assert cliente(segundo_docente).patch(url_miembro, {"activo": False}, format="json").status_code == 404
    assert estudiante.get(f"/api/v1/cursos/{curso['id']}/miembros/").status_code == 403
    assert docente.patch(url_miembro, {"activo": False}, format="json").status_code == 200
    assert estudiante.get(f"/api/v1/cursos/{curso['id']}/").status_code == 404
    assert estudiante.get("/api/v1/cursos/").json()["data"] == []
    assert estudiante.post("/api/v1/cursos/unirse/", {"token": curso["token_ingreso"]}, format="json").status_code == 403
    miembros = docente.get(f"/api/v1/cursos/{curso['id']}/miembros/").json()["data"]
    assert len(miembros) == 1
    assert miembros[0]["activo"] is False
    assert miembros[0]["estudiante_id"] == usuario_estudiante.id
    assert docente.patch(url_miembro, {"activo": True}, format="json").status_code == 200
    assert estudiante.post("/api/v1/cursos/unirse/", {"token": curso["token_ingreso"]}, format="json").status_code == 200
    assert MatriculaCursoModel.objects.count() == 1


@pytest.mark.django_db
def test_archivado_permite_lectura_a_matriculados_pero_no_ingreso_nuevo(usuario_docente, usuario_estudiante, otro_estudiante):
    docente, estudiante = cliente(usuario_docente), cliente(usuario_estudiante)
    curso = crear_curso(docente)
    estudiante.post("/api/v1/cursos/unirse/", {"codigo": curso["codigo_ingreso"]}, format="json")
    url = f"/api/v1/cursos/{curso['id']}/"
    assert docente.patch(url, {"activo": False}, format="json").status_code == 200
    assert estudiante.get(url).status_code == 200
    assert estudiante.get("/api/v1/cursos/").json()["data"][0]["activo"] is False
    assert estudiante.patch(url, {"activo": True}, format="json").status_code == 403
    assert cliente(otro_estudiante).post("/api/v1/cursos/unirse/", {"token": curso["token_ingreso"]}, format="json").status_code == 404
    assert docente.patch(url, {"activo": True}, format="json").status_code == 200
    assert cliente(otro_estudiante).post("/api/v1/cursos/unirse/", {"token": curso["token_ingreso"]}, format="json").status_code == 201


@pytest.mark.django_db
def test_detalle_curso_filtra_publicacion_y_borradores_pero_admite_creacion_sin_fuente(usuario_docente, usuario_estudiante):
    docente, estudiante = cliente(usuario_docente), cliente(usuario_estudiante)
    curso = crear_curso(docente)
    estudiante.post("/api/v1/cursos/unirse/", {"codigo": curso["codigo_ingreso"]}, format="json")
    activo = SistemaExpertoModel.objects.create(nombre="Publicado", estado="ACTIVO")
    borrador = SistemaExpertoModel.objects.create(nombre="Secreto", estado="BORRADOR")
    asignaciones = {}
    for nombre, tipo, sistema, estado in [
        ("Análisis publicado", "ANALISIS_BC", activo, "PUBLICADA"),
        ("Construcción", "CREACION_BC", None, "PUBLICADA"),
        ("Fuente suspendida", "ANALISIS_BC", borrador, "PUBLICADA"),
        ("Actividad no publicada", "ANALISIS_BC", activo, "BORRADOR"),
    ]:
        actividad = ActividadEducativaModel.objects.create(docente=usuario_docente, sistema_experto=sistema,
                                                           titulo=nombre, instrucciones="Prueba", tipo=tipo, estado=estado)
        asignaciones[nombre] = AsignacionActividadModel.objects.create(actividad=actividad, curso_id=curso["id"])
    url = f"/api/v1/cursos/{curso['id']}/"
    respuestas = estudiante.get(url).json()["data"]["asignaciones"]
    assert {a["actividad_titulo"] for a in respuestas} == {"Análisis publicado", "Construcción"}
    assert {a["tipo"] for a in respuestas} == {"ANALISIS_BC", "CREACION_BC"}
    assert {a["id"] for a in respuestas} == {str(asignaciones[n].id) for n in ["Análisis publicado", "Construcción"]}
    assert len(docente.get(url).json()["data"]["asignaciones"]) == 4


@pytest.mark.django_db
def test_preparacion_migracion_genera_invitaciones_unicas_sin_matricular_historicos(usuario_docente, usuario_estudiante):
    from importlib import import_module
    from django.apps import apps

    curso1 = CursoModel.objects.create(docente=usuario_docente, codigo="LEGADO-1", nombre="Existente 1")
    curso2 = CursoModel.objects.create(docente=usuario_docente, codigo="LEGADO-2", nombre="Existente 2")
    migracion = import_module("apps.actividades.migrations.0002_cursos_matriculas")
    migracion.preparar_invitaciones(apps, None)
    curso1.refresh_from_db()
    curso2.refresh_from_db()
    assert curso1.codigo == "LEGADO-1"
    assert curso2.codigo == "LEGADO-2"
    assert curso1.codigo_ingreso != curso2.codigo_ingreso
    assert curso1.token_ingreso != curso2.token_ingreso
    assert curso1.codigo_ingreso not in (curso1.codigo, curso2.codigo)
    assert curso2.codigo_ingreso not in (curso1.codigo, curso2.codigo)
    assert not MatriculaCursoModel.objects.exists()
