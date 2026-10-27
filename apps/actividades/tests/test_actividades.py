"""
Pruebas unitarias, de integración y de seguridad para el módulo de Actividades Educativas.
Sprint 2: HU-23, HU-24, HU-25.
"""
from uuid import uuid4
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status

from apps.actividades.services import (
    ActualizarActividadEducativa,
    AsignarActividadACurso,
    ConsultarActividadEducativa,
    ConsultarEntregaEstudiante,
    CrearActividadEducativa,
    CrearCurso,
    DesactivarActividadEducativa,
    EnviarEntrega,
    GuardarBorradorEntrega,
    ListarActividadesDocente,
    ListarActividadesParaEstudiante,
    ListarAsignaciones,
)
from apps.sistemas_expertos.services import CrearSistemaExperto
from compartido.constantes.enums import (
    DificultadActividad,
    EstadoActividad,
    EstadoAsignacion,
    EstadoEntrega,
)
from compartido.excepciones.base import (
    ExcepcionEntidadNoEncontrada,
    ExcepcionValidacionDominio,
)

User = get_user_model()


@pytest.fixture
def docente(db):
    user, _ = User.objects.get_or_create(
        username="profesor_test",
        defaults={"email": "profesor@test.edu", "is_staff": True},
    )
    user.groups.add(Group.objects.get(name="Docente"))
    return user


@pytest.fixture
def estudiante_1(db):
    user, _ = User.objects.get_or_create(
        username="estudiante_1",
        defaults={"email": "estudiante1@test.edu"},
    )
    user.groups.add(Group.objects.get(name="Estudiante"))
    return user


@pytest.fixture
def estudiante_2(db):
    user, _ = User.objects.get_or_create(
        username="estudiante_2",
        defaults={"email": "estudiante2@test.edu"},
    )
    user.groups.add(Group.objects.get(name="Estudiante"))
    return user


@pytest.fixture
def sistema_experto(db):
    # Las actividades resueltas por estudiantes requieren un sistema publicado.
    return CrearSistemaExperto().ejecutar(nombre="SE para Actividad Test", estado="ACTIVO")


@pytest.mark.django_db
def test_hu23_gestion_actividades_educativas(docente, sistema_experto):
    """HU-23: Crear, consultar, actualizar y desactivar una actividad educativa."""
    # 1. Crear actividad
    actividad = CrearActividadEducativa().ejecutar(
        docente_id=docente.id,
        sistema_experto_id=sistema_experto.id,
        titulo="Diagnostico con Factores de Certeza",
        instrucciones="Configure los hechos iniciales y verifique la conclusion alcanzada.",
        dificultad=DificultadActividad.MEDIA.value,
        estado=EstadoActividad.PUBLICADA.value,
    )
    assert actividad.id is not None
    assert actividad.titulo == "Diagnostico con Factores de Certeza"
    assert actividad.activa is True

    # 2. Consultar actividad
    consultada = ConsultarActividadEducativa().ejecutar(actividad.id)
    assert consultada.id == actividad.id

    # 3. Actualizar actividad
    actualizada = ActualizarActividadEducativa().ejecutar(
        id_actividad=actividad.id,
        docente_id=docente.id,
        titulo="Diagnostico Avanzado con Factores de Certeza",
        dificultad=DificultadActividad.AVANZADA.value,
    )
    assert actualizada.titulo == "Diagnostico Avanzado con Factores de Certeza"
    assert actualizada.dificultad == DificultadActividad.AVANZADA.value

    # 4. Desactivar actividad (baja logica)
    ok = DesactivarActividadEducativa().ejecutar(actividad.id, docente_id=docente.id)
    assert ok is True

    # Comprobar que ya no aparece como activa
    with pytest.raises(ExcepcionEntidadNoEncontrada):
        ConsultarActividadEducativa().ejecutar(actividad.id)


@pytest.mark.django_db
def test_hu24_asignar_actividad_a_curso(docente, sistema_experto):
    """HU-24: Asignar actividad a curso y prevenir duplicados."""
    # Crear curso
    curso = CrearCurso().ejecutar(
        codigo="IA-2026-I",
        nombre="Inteligencia Artificial I",
        docente_id=docente.id,
    )
    assert curso.codigo == "IA-2026-I"

    # Crear actividad
    actividad = CrearActividadEducativa().ejecutar(
        docente_id=docente.id,
        sistema_experto_id=sistema_experto.id,
        titulo="Taller de Inferencia Paso a Paso",
        instrucciones="Simule paso a paso.",
    )

    # Asignar actividad
    asignacion = AsignarActividadACurso().ejecutar(
        id_actividad=actividad.id,
        id_curso=curso.id,
        docente_id=docente.id,
    )
    assert asignacion.actividad_id == actividad.id
    assert asignacion.curso_id == curso.id
    assert asignacion.estado == EstadoAsignacion.VIGENTE.value

    # Intentar asignar nuevamente la misma actividad al mismo curso (debe rechazar)
    with pytest.raises(ExcepcionValidacionDominio, match="ya ha sido asignada"):
        AsignarActividadACurso().ejecutar(
            id_actividad=actividad.id,
            id_curso=curso.id,
            docente_id=docente.id,
        )


@pytest.mark.django_db
def test_hu25_flujo_resolucion_estudiante(docente, estudiante_1, estudiante_2, sistema_experto):
    """HU-25: Resolver actividad, guardar borrador, enviar y verificar aislamiento de entregas."""
    curso = CrearCurso().ejecutar(
        codigo="SIS-EX-01",
        nombre="Sistemas Basados en Conocimiento",
        docente_id=docente.id,
    )
    actividad = CrearActividadEducativa().ejecutar(
        docente_id=docente.id,
        sistema_experto_id=sistema_experto.id,
        titulo="Laboratorio 1",
        instrucciones="Ingrese hechos de prueba.",
        estado=EstadoActividad.PUBLICADA.value,
    )
    asignacion = AsignarActividadACurso().ejecutar(
        id_actividad=actividad.id,
        id_curso=curso.id,
        docente_id=docente.id,
    )

    # 1. Estudiante 1 lista actividades disponibles
    catalogo = ListarActividadesParaEstudiante().ejecutar(estudiante_id=estudiante_1.id)
    assert len(catalogo) >= 1
    item = next(c for c in catalogo if c["asignacion_id"] == asignacion.id)
    assert item["estado_entrega"] == "PENDIENTE"

    # 2. Estudiante 1 guarda borrador
    borrador = GuardarBorradorEntrega().ejecutar(
        id_asignacion=asignacion.id,
        estudiante_id=estudiante_1.id,
        solucion_texto="Borrador inicial: hechos fiebre y tos analizados.",
        hechos_ingresados=[{"nombre": "fiebre", "valor": True}],
    )
    assert borrador.estado == EstadoEntrega.BORRADOR.value

    # 3. Estudiante 1 envia entrega definitiva
    entrega_final = EnviarEntrega().ejecutar(
        id_asignacion=asignacion.id,
        estudiante_id=estudiante_1.id,
        solucion_texto="Solucion definitiva confirmada.",
        hechos_ingresados=[{"nombre": "fiebre", "valor": True, "fc": 0.8}],
    )
    assert entrega_final.estado == EstadoEntrega.ENVIADA.value
    assert entrega_final.fecha_envio is not None

    # 4. Intentar modificar la entrega ya enviada debe ser rechazado
    with pytest.raises(ExcepcionValidacionDominio, match="no admite modificaciones"):
        GuardarBorradorEntrega().ejecutar(
            id_asignacion=asignacion.id,
            estudiante_id=estudiante_1.id,
            solucion_texto="Intento de modificacion posterior",
        )

    # 5. Seguridad & IDOR: Estudiante 2 NO puede ver la entrega del Estudiante 1
    entrega_estudiante_2 = ConsultarEntregaEstudiante().ejecutar(
        id_asignacion=asignacion.id,
        usuario_id=estudiante_2.id,
        es_docente=False,
    )
    assert entrega_estudiante_2 is None  # Estudiante 2 no tiene entrega aun y no ve la de E1


@pytest.mark.django_db
def test_api_rest_actividades_y_entregas(api_client, docente, estudiante_1, sistema_experto):
    """Prueba integral de los endpoints REST de actividades, cursos, asignacion y entregas."""
    # 1. Crear curso por API
    api_client.force_authenticate(user=docente)
    resp_curso = api_client.post(
        reverse("actividades:cursos-list-create"),
        {"codigo": "API-101", "nombre": "Curso de Prueba API", "descripcion": "Desc"},
        format="json",
    )
    assert resp_curso.status_code == status.HTTP_201_CREATED
    curso_id = resp_curso.data["data"]["id"]

    # 2. Crear actividad por API
    resp_act = api_client.post(
        reverse("actividades:actividades-list-create"),
        {
            "sistema_experto_id": str(sistema_experto.id),
            "titulo": "Actividad API Test",
            "instrucciones": "Siga las instrucciones por API",
            "dificultad": "BASICA",
            "estado": "PUBLICADA",
        },
        format="json",
    )
    assert resp_act.status_code == status.HTTP_201_CREATED
    actividad_id = resp_act.data["data"]["id"]

    # 3. Asignar actividad al curso por API
    resp_asig = api_client.post(
        reverse("actividades:asignaciones-list-create"),
        {"actividad_id": actividad_id, "curso_id": curso_id},
        format="json",
    )
    assert resp_asig.status_code == status.HTTP_201_CREATED
    asignacion_id = resp_asig.data["data"]["id"]

    # 4. Estudiante consulta actividades disponibles
    api_client.force_authenticate(user=estudiante_1)
    inscripcion = api_client.post("/api/v1/cursos/unirse/", {"codigo": resp_curso.data["data"]["codigo_ingreso"]}, format="json")
    assert inscripcion.status_code == status.HTTP_201_CREATED
    resp_est_act = api_client.get(reverse("actividades:estudiante-actividades-list"))
    assert resp_est_act.status_code == status.HTTP_200_OK
    assert any(a["asignacion_id"] == asignacion_id for a in resp_est_act.data["data"])

    # 5. Estudiante guarda borrador por API
    url_entrega = reverse("actividades:entrega-borrador-detail", kwargs={"id_asignacion": asignacion_id})
    resp_borrador = api_client.post(
        url_entrega,
        {"solucion_texto": "Mi borrador via API", "hechos_ingresados": [{"nombre": "x", "valor": 10}]},
        format="json",
    )
    assert resp_borrador.status_code == status.HTTP_200_OK
    assert resp_borrador.data["data"]["estado"] == "BORRADOR"

    # 6. Estudiante envia entrega definitiva por API
    url_enviar = reverse("actividades:entrega-enviar", kwargs={"id_asignacion": asignacion_id})
    resp_enviar = api_client.post(
        url_enviar,
        {"solucion_texto": "Mi entrega enviada definitivamente via API", "hechos_ingresados": []},
        format="json",
    )
    assert resp_enviar.status_code == status.HTTP_200_OK
    assert resp_enviar.data["data"]["estado"] == "ENVIADA"
