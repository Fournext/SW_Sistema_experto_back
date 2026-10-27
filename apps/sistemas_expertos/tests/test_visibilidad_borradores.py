import pytest
from rest_framework.test import APIClient

from apps.base_conocimiento.models import (
    BaseConocimientoModel, CondicionModel, ConclusionModel, HechoModel, ReglaModel, VariableModel,
)
from apps.editor_visual.models import ConexionVisualModel, NodoVisualModel
from apps.inferencia.models import EjecucionInferenciaModel
from apps.sistemas_expertos.models import SistemaExpertoModel
from apps.validacion.models import ValidacionBaseModel


def cliente(usuario):
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


@pytest.fixture
def sistemas_visibles(db):
    def crear(nombre, estado):
        sistema = SistemaExpertoModel.objects.create(nombre=nombre, estado=estado)
        base = BaseConocimientoModel.objects.create(sistema_experto=sistema, nombre=f"Base {nombre}")
        hecho = HechoModel.objects.create(base_conocimiento=base, nombre="entrada", valor="true", tipo_dato="BOOLEANO")
        variable = VariableModel.objects.create(base_conocimiento=base, nombre="salida")
        regla = ReglaModel.objects.create(base_conocimiento=base, nombre="R1", prioridad=1)
        condicion = CondicionModel.objects.create(regla=regla, hecho=hecho, operador="=", valor_esperado="true")
        conclusion = ConclusionModel.objects.create(regla=regla, variable_resultante=variable, valor_resultante="resultado")
        nodo = NodoVisualModel.objects.create(sistema_experto=sistema, tipo="HECHO", referencia_id=hecho.id)
        otro_nodo = NodoVisualModel.objects.create(sistema_experto=sistema, tipo="REGLA", referencia_id=regla.id)
        conexion = ConexionVisualModel.objects.create(sistema_experto=sistema, nodo_origen=nodo, nodo_destino=otro_nodo)
        ejecucion = EjecucionInferenciaModel.objects.create(sistema_experto=sistema, estado="INICIADA", es_simulacion=True)
        validacion = ValidacionBaseModel.objects.create(base_conocimiento=base)
        return {"sistema": sistema, "base": base, "hecho": hecho, "variable": variable,
                "regla": regla, "condicion": condicion, "conclusion": conclusion, "nodo": nodo,
                "conexion": conexion, "ejecucion": ejecucion, "validacion": validacion}

    return {"activo": crear("Visible", "ACTIVO"), "borrador": crear("Secreto docente", "BORRADOR")}


@pytest.mark.django_db
def test_lista_oculta_borradores_a_estudiante_pero_docente_y_superusuario_los_ven(
    usuario_estudiante, usuario_docente, superusuario, sistemas_visibles,
):
    activo = str(sistemas_visibles["activo"]["sistema"].id)
    borrador = str(sistemas_visibles["borrador"]["sistema"].id)
    for usuario, esperados in ((usuario_estudiante, {activo}), (usuario_docente, {activo, borrador}), (superusuario, {activo, borrador})):
        respuesta = cliente(usuario).get("/api/v1/sistemas-expertos/")
        assert respuesta.status_code == 200
        assert {s["id"] for s in respuesta.json()["data"]} == esperados


@pytest.mark.django_db
def test_solo_docente_puede_activar_y_activacion_hace_visible_el_sistema(
    usuario_estudiante, usuario_docente, sistemas_visibles,
):
    estudiante = cliente(usuario_estudiante)
    docente = cliente(usuario_docente)
    sistema = sistemas_visibles["borrador"]["sistema"]
    url = f"/api/v1/sistemas-expertos/{sistema.id}/"
    assert estudiante.get(url).status_code == 404
    assert estudiante.patch(url, {"estado": "ACTIVO"}, format="json").status_code == 404
    sistema.refresh_from_db()
    assert sistema.estado == "BORRADOR"
    respuesta = docente.patch(url, {"estado": "ACTIVO"}, format="json")
    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["estado"] == "ACTIVO"
    assert estudiante.get(url).status_code == 200
    assert str(sistema.id) in {s["id"] for s in estudiante.get("/api/v1/sistemas-expertos/").json()["data"]}
    assert estudiante.patch(url, {"estado": "BORRADOR"}, format="json").status_code == 403
    sistema.refresh_from_db()
    assert sistema.estado == "ACTIVO"
    assert estudiante.post("/api/v1/sistemas-expertos/", {"nombre": "No autorizado"}, format="json").status_code == 403
    assert estudiante.delete(url).status_code == 403


@pytest.mark.django_db
def test_uuid_anidados_e_indirectos_de_borrador_no_exponen_conocimiento_ni_historial(
    usuario_estudiante, usuario_docente, sistemas_visibles,
):
    estudiante = cliente(usuario_estudiante)
    docente = cliente(usuario_docente)
    d = sistemas_visibles["borrador"]
    rutas = [
        f"sistemas-expertos/{d['sistema'].id}/", f"sistemas-expertos/{d['sistema'].id}/base-conocimiento/",
        f"bases-conocimiento/{d['base'].id}/hechos/", f"bases-conocimiento/{d['base'].id}/variables/",
        f"bases-conocimiento/{d['base'].id}/reglas/", f"sistemas-expertos/{d['sistema'].id}/editor/",
        f"hechos/{d['hecho'].id}/", f"variables/{d['variable'].id}/", f"reglas/{d['regla'].id}/",
        f"condiciones/{d['condicion'].id}/", f"conclusiones/{d['conclusion'].id}/",
        f"nodos/{d['nodo'].id}/", f"conexiones/{d['conexion'].id}/",
        f"inferencias/{d['ejecucion'].id}/", f"inferencias/{d['ejecucion'].id}/detalles/",
        f"inferencias/{d['ejecucion'].id}/pasos/", f"inferencias/{d['ejecucion'].id}/hechos-inferidos/",
        f"inferencias/{d['ejecucion'].id}/conflictos/", f"inferencias/{d['ejecucion'].id}/explicacion/",
        f"ejecuciones/{d['ejecucion'].id}/hechos-inferidos/", f"ejecuciones/{d['ejecucion'].id}/conflictos/",
        f"ejecuciones/{d['ejecucion'].id}/explicacion/",
        f"bases-conocimiento/{d['base'].id}/validaciones/ultima/",
        f"validaciones/{d['validacion'].id}/", f"validaciones/{d['validacion'].id}/incidencias/",
    ]
    for ruta in rutas:
        respuesta = estudiante.get(f"/api/v1/{ruta}")
        assert respuesta.status_code == 404, (ruta, respuesta.status_code, respuesta.content)
        assert b"Secreto docente" not in respuesta.content
    # El mismo UUID existe y el docente sí puede consultarlo.
    assert docente.get(f"/api/v1/sistemas-expertos/{d['sistema'].id}/").status_code == 200
    assert docente.get(f"/api/v1/hechos/{d['hecho'].id}/").status_code == 200
    activo = sistemas_visibles["activo"]
    assert estudiante.get(f"/api/v1/sistemas-expertos/{activo['sistema'].id}/").status_code == 200
    assert estudiante.get(f"/api/v1/hechos/{activo['hecho'].id}/").status_code == 200


@pytest.mark.django_db
def test_borrador_tampoco_admite_acciones_por_uuid_ni_metodos_alternativos(usuario_estudiante, sistemas_visibles):
    estudiante = cliente(usuario_estudiante)
    d = sistemas_visibles["borrador"]
    rutas_post = [
        f"sistemas-expertos/{d['sistema'].id}/inferencias/", f"sistemas-expertos/{d['sistema'].id}/simulaciones/",
        f"sistemas-expertos/{d['sistema'].id}/simulaciones/iniciar/", f"sistemas-expertos/{d['sistema'].id}/nodos/",
        f"sistemas-expertos/{d['sistema'].id}/conexiones/", f"bases-conocimiento/{d['base'].id}/validar/",
        f"reglas/{d['regla'].id}/condiciones/", f"reglas/{d['regla'].id}/conclusiones/",
        f"simulaciones/{d['ejecucion'].id}/paso/", f"inferencias/{d['ejecucion'].id}/paso/",
        f"simulaciones/{d['ejecucion'].id}/control/", f"inferencias/{d['ejecucion'].id}/control/",
    ]
    for prefijo in ("simulaciones", "inferencias"):
        rutas_post.extend(f"{prefijo}/{d['ejecucion'].id}/{accion}/" for accion in ("pausar", "continuar", "reiniciar", "finalizar"))
    for ruta in rutas_post:
        respuesta = estudiante.post(f"/api/v1/{ruta}", {"accion": "REINICIAR"}, format="json")
        assert respuesta.status_code == 404, (ruta, respuesta.status_code, respuesta.content)
    for prefijo, recurso in (("hechos", "hecho"), ("reglas", "regla"), ("variables", "variable"),
                             ("condiciones", "condicion"), ("conclusiones", "conclusion"),
                             ("nodos", "nodo"), ("conexiones", "conexion")):
        url = f"/api/v1/{prefijo}/{d[recurso].id}/"
        for metodo in ("put", "patch", "delete", "options", "head"):
            respuesta = getattr(estudiante, metodo)(url, {}, format="json")
            assert respuesta.status_code == 404, (metodo, url, respuesta.status_code)
    assert SistemaExpertoModel.objects.filter(id=d["sistema"].id, estado="BORRADOR").exists()
    assert HechoModel.objects.filter(id=d["hecho"].id, valor="true").exists()
    assert EjecucionInferenciaModel.objects.filter(id=d["ejecucion"].id, estado="INICIADA").exists()


@pytest.mark.django_db
def test_historial_global_filtra_borradores_y_filtro_explicito_no_los_revela(
    usuario_estudiante, usuario_docente, sistemas_visibles,
):
    estudiante = cliente(usuario_estudiante)
    docente = cliente(usuario_docente)
    activo, borrador = sistemas_visibles["activo"], sistemas_visibles["borrador"]
    for ruta in ("inferencias", "historial-inferencias"):
        respuesta = estudiante.get(f"/api/v1/{ruta}/")
        assert respuesta.status_code == 200
        assert {r["id"] for r in respuesta.json()["data"]} == {str(activo["ejecucion"].id)}
        respuesta = docente.get(f"/api/v1/{ruta}/")
        assert respuesta.status_code == 200
        assert {r["id"] for r in respuesta.json()["data"]} == {str(activo["ejecucion"].id), str(borrador["ejecucion"].id)}
        respuesta = estudiante.get(f"/api/v1/{ruta}/", {"sistema_experto_id": str(borrador["sistema"].id)})
        assert respuesta.status_code == 404
        respuesta = estudiante.get(f"/api/v1/{ruta}/", {"sistema_experto_id": str(activo["sistema"].id)})
        assert respuesta.status_code == 200
        assert len(respuesta.json()["data"]) == 1


@pytest.mark.django_db
def test_admin_central_no_recibe_permisos_operativos_ni_acceso_a_borradores(usuario_admin_central, sistemas_visibles):
    central = cliente(usuario_admin_central)
    activo = sistemas_visibles["activo"]["sistema"]
    borrador = sistemas_visibles["borrador"]["sistema"]
    assert central.get("/api/v1/sistemas-expertos/").status_code == 403
    assert central.patch(f"/api/v1/sistemas-expertos/{activo.id}/", {"estado": "BORRADOR"}, format="json").status_code == 403
    assert central.get(f"/api/v1/sistemas-expertos/{borrador.id}/").status_code == 404


@pytest.mark.django_db
def test_actividades_y_asignaciones_no_revelan_borradores_por_lista_uuid_o_cuerpo(
    usuario_estudiante, usuario_docente, sistemas_visibles,
):
    from apps.actividades.models import ActividadEducativaModel, AsignacionActividadModel, CursoModel

    estudiante, docente = cliente(usuario_estudiante), cliente(usuario_docente)
    curso = CursoModel.objects.create(codigo="VIS-1", nombre="Visibilidad", docente=usuario_docente)
    actividades, asignaciones = {}, {}
    for nombre, datos in sistemas_visibles.items():
        actividad = ActividadEducativaModel.objects.create(
            docente=usuario_docente, sistema_experto=datos["sistema"],
            titulo=f"Actividad {nombre}", instrucciones="Privadas si el sistema no está publicado", estado="PUBLICADA",
        )
        actividades[nombre] = actividad
        asignaciones[nombre] = AsignacionActividadModel.objects.create(actividad=actividad, curso=curso)
    # Una actividad histórica a nombre del estudiante tampoco debe filtrar el sistema.
    ActividadEducativaModel.objects.create(docente=usuario_estudiante, sistema_experto=sistemas_visibles["borrador"]["sistema"],
                                           titulo="Borrador histórico", instrucciones="No visible")
    assert estudiante.get("/api/v1/actividades/").json()["data"] == []
    assert len(docente.get("/api/v1/actividades/").json()["data"]) == 2
    from apps.actividades.models import MatriculaCursoModel
    MatriculaCursoModel.objects.create(curso=curso, estudiante=usuario_estudiante)
    respuesta = estudiante.get("/api/v1/estudiante/actividades/")
    assert respuesta.status_code == 200
    assert {r["actividad_id"] for r in respuesta.json()["data"]} == {str(actividades["activo"].id)}
    respuesta = estudiante.get("/api/v1/asignaciones/")
    assert respuesta.status_code == 200
    assert {r["id"] for r in respuesta.json()["data"]} == {str(asignaciones["activo"].id)}
    assert estudiante.get(f"/api/v1/actividades/{actividades['borrador'].id}/").status_code == 404
    assert estudiante.get(f"/api/v1/asignaciones/{asignaciones['borrador'].id}/entrega/").status_code == 404
    assert docente.get(f"/api/v1/actividades/{actividades['borrador'].id}/").status_code == 200
    respuesta = estudiante.post("/api/v1/actividades/", {
        "sistema_experto_id": str(sistemas_visibles["borrador"]["sistema"].id), "titulo": "Intento", "instrucciones": "Intento",
    }, format="json")
    assert respuesta.status_code == 403
    respuesta = estudiante.post("/api/v1/asignaciones/", {
        "actividad_id": str(actividades["borrador"].id), "curso_id": str(curso.id),
    }, format="json")
    assert respuesta.status_code == 403
    assert ActividadEducativaModel.objects.count() == 3
    assert AsignacionActividadModel.objects.count() == 2
