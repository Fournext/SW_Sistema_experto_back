import copy
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.actividades.models import (ActividadEducativaModel, AsignacionActividadModel, CursoModel,
    MatriculaCursoModel, EntregaActividadModel, RevisionEntregaModel)
from apps.base_conocimiento.models import BaseConocimientoModel, HechoModel, ReglaModel, CondicionModel, ConclusionModel
from apps.inferencia.models import EjecucionInferenciaModel
from apps.sistemas_expertos.models import SistemaExpertoModel


def cliente(usuario):
    client = APIClient()
    client.force_authenticate(usuario)
    return client


@pytest.fixture
def actividad_contextual(usuario_docente, usuario_estudiante):
    sistema = SistemaExpertoModel.objects.create(nombre="Fuente docente", estado="ACTIVO", created_by=usuario_docente)
    base = BaseConocimientoModel.objects.create(sistema_experto=sistema, nombre="BC fuente")
    entrada = HechoModel.objects.create(base_conocimiento=base, nombre="entrada", valor="true", tipo_dato="BOOLEANO", es_inicial=True, pregunta="¿Entrada?")
    salida = HechoModel.objects.create(base_conocimiento=base, nombre="salida", valor=None, tipo_dato="TEXTO", es_inicial=False)
    regla = ReglaModel.objects.create(base_conocimiento=base, nombre="REGLA_SECRETA", prioridad=1)
    condicion = CondicionModel.objects.create(regla=regla, hecho=entrada, operador="=", valor_esperado="true")
    ConclusionModel.objects.create(regla=regla, hecho_resultante=salida, valor_resultante="APROBADO")
    curso = CursoModel.objects.create(codigo="CTX-1", nombre="Curso contextual", docente=usuario_docente)
    MatriculaCursoModel.objects.create(curso=curso, estudiante=usuario_estudiante)
    actividad = ActividadEducativaModel.objects.create(docente=usuario_docente, sistema_experto=sistema,
        titulo="Análisis", instrucciones="Resolver", tipo="ANALISIS_BC", estado="PUBLICADA",
        permisos={"ver_bc": False, "editar_bc": False, "editor_visual": False,
                  "inferencia_directa": True, "simulacion": True, "validacion": False, "trazabilidad": False})
    asignacion = AsignacionActividadModel.objects.create(actividad=actividad, curso=curso)
    return dict(sistema=sistema, base=base, entrada=entrada, salida=salida, regla=regla, condicion=condicion,
        curso=curso, actividad=actividad, asignacion=asignacion,
        alumno=cliente(usuario_estudiante), docente=cliente(usuario_docente), usuario=usuario_estudiante)


def trabajo(d, ruta):
    return f"/api/v1/asignaciones/{d['asignacion'].id}/trabajo/{ruta}"


@pytest.mark.django_db
def test_inferencia_contextual_no_amplia_permisos_y_no_revela_bc_ni_trazas(actividad_contextual):
    d = actividad_contextual
    a = d["alumno"]
    assert a.get("/api/v1/sistemas-expertos/").json()["data"] == []
    assert a.get(f"/api/v1/hechos/{d['entrada'].id}/").status_code == 404
    assert a.post(f"/api/v1/sistemas-expertos/{d['sistema'].id}/inferencias/", {}, format="json").status_code == 404
    contexto = a.get(f"/api/v1/asignaciones/{d['asignacion'].id}/").json()["data"]
    assert contexto["puede_editar"] is True  # Puede responder y entregar aunque la BC sea de solo lectura.
    meta = a.get(trabajo(d, f"sistemas-expertos/{d['sistema'].id}/base-conocimiento/")).json()["data"]
    assert not any(k in meta for k in ("hechos", "variables", "reglas"))
    assert a.get(trabajo(d, f"bases-conocimiento/{d['base'].id}/hechos/")).status_code == 403
    entradas = a.get(trabajo(d, "entradas/")).json()["data"]
    assert [e["nombre"] for e in entradas] == ["entrada"]
    prevalidacion = a.post(trabajo(d, f"bases-conocimiento/{d['base'].id}/validar/"), {}, format="json")
    assert prevalidacion.status_code in (200, 201)
    assert b"REGLA_SECRETA" not in prevalidacion.content
    res = a.post(trabajo(d, f"sistemas-expertos/{d['sistema'].id}/inferencias/"), {}, format="json")
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["conclusion_final"] == "APROBADO"
    assert b"REGLA_SECRETA" not in res.content
    assert "reglas_evaluadas" not in data
    ejecucion = EjecucionInferenciaModel.objects.get(pk=data["ejecucion_id"])
    assert ejecucion.asignacion_id == d["asignacion"].id
    assert ejecucion.estudiante_id == d["usuario"].id
    assert ejecucion.bc_snapshot["reglas"][0]["nombre"] == "REGLA_SECRETA"
    assert a.get(trabajo(d, f"inferencias/{ejecucion.id}/detalles/")).status_code == 403
    assert a.get(trabajo(d, "inferencias/")).json()["data"][0]["id"] == str(ejecucion.id)


@pytest.mark.django_db
def test_sesion_congela_bc_usada_y_nueva_ejecucion_usa_fuente_actual(actividad_contextual):
    d = actividad_contextual
    d["actividad"].permisos.update(ver_bc=True, trazabilidad=True)
    d["actividad"].save()
    res = d["alumno"].post(trabajo(d, f"sistemas-expertos/{d['sistema'].id}/simulaciones/"), {}, format="json")
    assert res.status_code == 201
    id_sesion = res.json()["data"]["id"]
    d["condicion"].valor_esperado = "false"
    d["condicion"].save()
    d["regla"].nombre = "NOMBRE_NUEVO"
    d["regla"].save()
    respuesta = d["alumno"].post(trabajo(d, f"simulaciones/{id_sesion}/paso/"), {"modo_evaluacion": "POR_REGLA"}, format="json")
    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["conclusion_final"] == "APROBADO"
    explicacion = d["alumno"].get(trabajo(d, f"inferencias/{id_sesion}/explicacion/"))
    assert explicacion.status_code == 200
    assert explicacion.json()["data"]["reglas_disparadas"][0]["nombre"] == "REGLA_SECRETA"
    assert explicacion.json()["data"]["reglas_disparadas"][0]["condiciones_cumplidas"] == ["entrada = true"]
    nueva = d["alumno"].post(trabajo(d, f"sistemas-expertos/{d['sistema'].id}/inferencias/"), {}, format="json")
    assert nueva.status_code == 201
    assert nueva.json()["data"]["conclusion_final"] is None


@pytest.mark.django_db
def test_aislamiento_ejecuciones_matricula_revocada_y_fuente_suspendida(actividad_contextual, usuario_estudiante):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    d = actividad_contextual
    otro = get_user_model().objects.create_user(username="otro_contexto", password="Password123*")
    otro.groups.add(Group.objects.get(name="Estudiante"))
    MatriculaCursoModel.objects.create(curso=d["curso"], estudiante=otro)
    sin_matricula = cliente(otro)
    MatriculaCursoModel.objects.filter(estudiante=otro).update(activo=False)
    assert sin_matricula.get(f"/api/v1/asignaciones/{d['asignacion'].id}/").status_code == 404
    MatriculaCursoModel.objects.filter(estudiante=otro).update(activo=True)
    res = d["alumno"].post(trabajo(d, f"sistemas-expertos/{d['sistema'].id}/inferencias/"), {}, format="json")
    id_ejecucion = res.json()["data"]["ejecucion_id"]
    assert sin_matricula.get(trabajo(d, f"inferencias/{id_ejecucion}/")).status_code == 404
    assert d["docente"].get(f"/api/v1/inferencias/{id_ejecucion}/").status_code == 404
    d["actividad"].permisos["inferencia_directa"] = False
    d["actividad"].save()
    assert d["alumno"].post(trabajo(d, f"sistemas-expertos/{d['sistema'].id}/inferencias/"), {}, format="json").status_code == 403
    d["sistema"].estado = "BORRADOR"
    d["sistema"].save()
    assert d["alumno"].get(trabajo(d, "entradas/")).status_code == 404
    d["sistema"].estado = "ACTIVO"
    d["sistema"].save()
    MatriculaCursoModel.objects.filter(estudiante=d["usuario"]).update(activo=False)
    assert d["alumno"].get(trabajo(d, f"inferencias/{id_ejecucion}/")).status_code == 404


@pytest.mark.django_db
def test_revision_inmutable_redaccion_reapertura_y_comentario_solo_docente(actividad_contextual):
    d = actividad_contextual
    res = d["alumno"].post(trabajo(d, f"sistemas-expertos/{d['sistema'].id}/inferencias/"), {}, format="json")
    id_ejecucion = res.json()["data"]["ejecucion_id"]
    entrega_url = f"/api/v1/asignaciones/{d['asignacion'].id}/entrega/"
    envio_url = f"/api/v1/asignaciones/{d['asignacion'].id}/enviar/"
    borrador = d["alumno"].post(entrega_url, {"solucion_texto": "Primer borrador"}, format="json")
    assert borrador.status_code == 200
    id_entrega = borrador.json()["data"]["id"]
    assert d["docente"].get(f"/api/v1/entregas/{id_entrega}/").status_code == 404
    enviado = d["alumno"].post(envio_url, {"solucion_texto": "Enviado estable", "ejecucion_inferencia_id": id_ejecucion}, format="json")
    assert enviado.status_code == 200
    assert b"REGLA_SECRETA" not in enviado.content
    snapshot = copy.deepcopy(RevisionEntregaModel.objects.get(entrega_id=id_entrega).snapshot)
    assert snapshot["bc"]["reglas"][0]["nombre"] == "REGLA_SECRETA"
    assert d["alumno"].post(entrega_url, {"solucion_texto": "Cambio prohibido"}, format="json").status_code == 403
    comentario_url = f"/api/v1/entregas/{id_entrega}/comentarios/"
    assert d["alumno"].post(comentario_url, {"texto": "No docente"}, format="json").status_code == 403
    assert d["docente"].post(comentario_url, {"texto": "Revisar"}, format="json").status_code == 201
    d["asignacion"].fecha_limite = timezone.now() - timedelta(days=1)
    d["asignacion"].save()
    reabrir = f"/api/v1/entregas/{id_entrega}/reabrir/"
    assert d["docente"].post(reabrir, {}, format="json").status_code == 400
    assert d["docente"].post(reabrir, {"fecha_limite": None}, format="json").status_code == 200
    assert d["alumno"].post(entrega_url, {"solucion_texto": "SECRETO_BORRADOR_NUEVO"}, format="json").status_code == 200
    revision_docente = d["docente"].get(f"/api/v1/entregas/{id_entrega}/")
    assert revision_docente.status_code == 200
    assert b"SECRETO_BORRADOR_NUEVO" not in revision_docente.content
    assert revision_docente.json()["data"]["revisiones"][0]["snapshot"] == snapshot
    reenviado = d["alumno"].post(envio_url, {"solucion_texto": "Segunda revisión"}, format="json")
    assert reenviado.status_code == 200
    assert reenviado.json()["data"]["numero_revision"] == 2
    assert RevisionEntregaModel.objects.get(entrega_id=id_entrega, numero=1).snapshot == snapshot


@pytest.mark.django_db
def test_creacion_privada_permisos_archivo_y_no_escape_por_uuid(actividad_contextual):
    d = actividad_contextual
    d["actividad"].tipo = "CREACION_BC"
    d["actividad"].sistema_experto = None
    d["actividad"].permisos = {}
    d["actividad"].save()
    ctx = d["alumno"].get(f"/api/v1/asignaciones/{d['asignacion'].id}/").json()["data"]
    sistema_id = ctx["trabajo_sistema_id"]
    sistema = SistemaExpertoModel.objects.get(pk=sistema_id)
    assert sistema.estado == "BORRADOR"
    assert sistema.created_by_id == d["usuario"].id
    assert d["alumno"].get(f"/api/v1/sistemas-expertos/{sistema_id}/").status_code == 404
    assert d["docente"].get(f"/api/v1/sistemas-expertos/{sistema_id}/").status_code == 404
    base = BaseConocimientoModel.objects.get(sistema_experto=sistema)
    ruta = trabajo(d, f"bases-conocimiento/{base.id}/hechos/")
    assert d["alumno"].post(ruta, {"nombre": "privado", "valor": None}, format="json").status_code == 201
    assert d["alumno"].post(trabajo(d, f"sistemas-expertos/{sistema_id}/inferencias/"), {}, format="json").status_code == 403
    assert d["alumno"].get(trabajo(d, f"hechos/{d['entrada'].id}/")).status_code == 404
    d["curso"].activo = False
    d["curso"].save()
    assert d["alumno"].get(ruta).status_code == 200
    assert d["alumno"].post(ruta, {"nombre": "prohibido"}, format="json").status_code == 403
    assert d["alumno"].post(f"/api/v1/asignaciones/{d['asignacion'].id}/enviar/", {"solucion_texto": "cerrado"}, format="json").status_code == 403
