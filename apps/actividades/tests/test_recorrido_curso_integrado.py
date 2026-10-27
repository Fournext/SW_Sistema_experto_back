"""Recorrido de docente y estudiante usando las rutas reales de la aplicación."""
import pytest
from rest_framework.test import APIClient


def cliente(usuario):
    api = APIClient()
    api.force_authenticate(user=usuario)
    return api


def datos(respuesta, estado=200):
    assert respuesta.status_code == estado, respuesta.content
    return respuesta.json()["data"]


@pytest.mark.django_db
def test_recorrido_curso_creacion_bc_entrega_comentario_y_reapertura(usuario_docente, usuario_estudiante):
    docente, estudiante = cliente(usuario_docente), cliente(usuario_estudiante)
    curso = datos(docente.post("/api/v1/cursos/", {"nombre": "Bases de conocimiento", "codigo": "BC-2026"}, format="json"), 201)
    datos(estudiante.post("/api/v1/cursos/unirse/", {"codigo": curso["codigo_ingreso"]}, format="json"), 201)
    actividad = datos(docente.post("/api/v1/actividades/", {
        "titulo": "Construir una BC de acceso", "instrucciones": "Modela una condición de edad y explica tu solución.",
        "tipo": "CREACION_BC", "estado": "PUBLICADA", "curso_id": curso["id"],
        "permisos": {"ver_bc": True, "editar_bc": True, "editor_visual": True, "inferencia_directa": True,
                     "simulacion": False, "validacion": False, "trazabilidad": True},
    }, format="json"), 201)
    asignacion = actividad["asignacion_id"]
    contexto = datos(estudiante.get(f"/api/v1/asignaciones/{asignacion}/"))
    sistema = contexto["trabajo_sistema_id"]
    prefijo = f"/api/v1/asignaciones/{asignacion}/trabajo"
    base = datos(estudiante.get(f"{prefijo}/sistemas-expertos/{sistema}/base-conocimiento/"))
    hecho = datos(estudiante.post(f"{prefijo}/bases-conocimiento/{base['id']}/hechos/", {
        "nombre": "Edad", "tipo_dato": "ENTERO", "es_inicial": True,
    }, format="json"), 201)
    variable = datos(estudiante.post(f"{prefijo}/bases-conocimiento/{base['id']}/variables/", {
        "nombre": "Acceso", "tipo_dato": "TEXTO",
    }, format="json"), 201)
    regla = datos(estudiante.post(f"{prefijo}/bases-conocimiento/{base['id']}/reglas/", {
        "nombre": "R1", "prioridad": 10, "activa": True,
    }, format="json"), 201)
    datos(estudiante.post(f"{prefijo}/reglas/{regla['id']}/condiciones/", {
        "hecho_id": hecho["id"], "operador": ">=", "valor_esperado": "18",
    }, format="json"), 201)
    datos(estudiante.post(f"{prefijo}/reglas/{regla['id']}/conclusiones/", {
        "variable_resultante_id": variable["id"], "valor_resultante": "Aprobado",
    }, format="json"), 201)
    # La validación automática previa debe funcionar aunque su pantalla no esté habilitada.
    validacion = datos(estudiante.post(f"{prefijo}/bases-conocimiento/{base['id']}/validar/", {}, format="json"), 201)
    assert validacion["es_valida"] is True
    ejecucion = datos(estudiante.post(f"{prefijo}/sistemas-expertos/{sistema}/inferencias/", {
        "hechos_iniciales": [{"nombre": "Edad", "valor": "20", "tipo_dato": "ENTERO"}],
    }, format="json"), 201)
    assert ejecucion["conclusion_final"] == "Aprobado"
    # El espacio privado no puede abrirse desde rutas generales.
    assert estudiante.get(f"/api/v1/sistemas-expertos/{sistema}/").status_code == 404
    entrega = datos(estudiante.post(f"/api/v1/asignaciones/{asignacion}/enviar/", {
        "solucion_texto": "Una edad de 20 años permite el acceso.",
        "ejecuciones_ids": [ejecucion["ejecucion_id"]],
    }, format="json"))
    assert entrega["estado"] == "ENVIADA"
    detalle = datos(docente.get(f"/api/v1/entregas/{entrega['id']}/"))
    primera = detalle["revisiones"][0]
    assert primera["snapshot"]["bc"]["reglas"][0]["nombre"] == "R1"
    assert primera["snapshot"]["ejecuciones"][0]["conclusion_final"] == "Aprobado"
    datos(docente.post(f"/api/v1/entregas/{entrega['id']}/comentarios/", {
        "texto": "Explica también el caso de una edad menor.", "revision_id": primera["id"],
    }, format="json"), 201)
    alumno = datos(estudiante.get(f"/api/v1/asignaciones/{asignacion}/entrega/"))
    assert alumno["revisiones"][0]["comentarios"][0]["texto"] == "Explica también el caso de una edad menor."
    assert estudiante.post(f"/api/v1/entregas/{entrega['id']}/comentarios/", {"texto": "No soy docente"}, format="json").status_code == 403
    assert estudiante.patch(f"{prefijo}/hechos/{hecho['id']}/", {"valor": "99"}, format="json").status_code == 403
    datos(docente.post(f"/api/v1/entregas/{entrega['id']}/reabrir/", {"fecha_limite": None}, format="json"))
    datos(estudiante.post(f"/api/v1/asignaciones/{asignacion}/entrega/", {
        "solucion_texto": "Este borrador nuevo aún no puede verlo el docente.",
    }, format="json"))
    anterior = datos(docente.get(f"/api/v1/entregas/{entrega['id']}/"))
    assert "Este borrador nuevo" not in str(anterior)
    assert anterior["revisiones"][0]["snapshot"] == primera["snapshot"]
    segunda = datos(estudiante.post(f"/api/v1/asignaciones/{asignacion}/enviar/", {
        "solucion_texto": "La condición no se cumple si la edad es menor de 18.",
    }, format="json"))
    assert segunda["numero_revision"] == 2
    final = datos(docente.get(f"/api/v1/entregas/{entrega['id']}/"))
    assert len(final["revisiones"]) == 2
    assert final["revisiones"][0]["snapshot"] == primera["snapshot"]
