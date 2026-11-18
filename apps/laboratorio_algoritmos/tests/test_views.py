import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.laboratorio_algoritmos.models import ProgramaAlgoritmoModel

User = get_user_model()


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        username="estudiante1",
        email="estudiante1@test.com",
        password="Password123!",
        nombre_completo="Juan Perez",
    )


@pytest.fixture
def api_client(usuario):
    client = APIClient()
    client.force_authenticate(user=usuario)
    return client


@pytest.mark.django_db
def test_compilar_codigo_valido(api_client):
    codigo = """
    void main(Lista<Regla> R, BaseHechos BH) {
        int i = 0;
        println("Hola mundo");
    }
    """
    res = api_client.post("/api/v1/laboratorio/compilar/", {"codigo_fuente": codigo}, format="json")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valido"] is True
    assert len(data["errores"]) == 0


@pytest.mark.django_db
def test_compilar_codigo_error_sintaxis(api_client):
    codigo = """
    void main(Lista<Regla> R {
        int i = 0;
    }
    """
    res = api_client.post("/api/v1/laboratorio/compilar/", {"codigo_fuente": codigo}, format="json")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valido"] is False
    assert len(data["errores"]) > 0


@pytest.mark.django_db
def test_plantillas_api(api_client):
    res = api_client.get("/api/v1/laboratorio/plantillas/")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 3
    assert any("fwc-secuencial-clasico" in p["id"] for p in data)


@pytest.mark.django_db
def test_crud_programas_algoritmo(api_client, usuario):
    # Crear programa
    res_crear = api_client.post(
        "/api/v1/laboratorio/programas/",
        {
            "titulo": "Mi Algoritmo FWC",
            "descripcion": "Prueba de laboratorio",
            "codigo_fuente": "void main(Lista<Regla> R, BaseHechos BH) { int i = 1; }",
        },
        format="json",
    )
    assert res_crear.status_code == 201
    prog_id = res_crear.json()["data"]["id"]

    # Consultar detalle
    res_get = api_client.get(f"/api/v1/laboratorio/programas/{prog_id}/")
    assert res_get.status_code == 200
    assert res_get.json()["data"]["titulo"] == "Mi Algoritmo FWC"

    # Actualizar programa (debe crear una nueva revisión)
    res_patch = api_client.patch(
        f"/api/v1/laboratorio/programas/{prog_id}/",
        {
            "codigo_fuente": "void main(Lista<Regla> R, BaseHechos BH) { int i = 2; }",
        },
        format="json",
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["data"]["version_entero"] == 2

    # Consultar revisiones
    res_revs = api_client.get(f"/api/v1/laboratorio/programas/{prog_id}/revisiones/")
    assert res_revs.status_code == 200
    assert len(res_revs.json()["data"]) == 2


@pytest.mark.django_db
def test_iniciar_y_avanzar_corrida(api_client, usuario):
    codigo = """
    void main(Lista<Regla> R, BaseHechos BH) {
        int x = 10;
        int y = 20;
        int z = x + y;
        println("Resultado z = " + z);
    }
    """
    # 1. Iniciar corrida
    res_init = api_client.post(
        "/api/v1/laboratorio/ejecutar/",
        {
            "codigo_fuente": codigo,
        },
        format="json",
    )
    assert res_init.status_code == 201
    corrida_id = res_init.json()["data"]["id"]
    assert res_init.json()["data"]["estado"] == "EJECUTANDO"

    # 2. Avanzar paso
    res_step = api_client.post(
        f"/api/v1/laboratorio/corridas/{corrida_id}/avanzar/",
        {"modo": "LINE_STEP", "max_pasos": 1},
        format="json",
    )
    assert res_step.status_code == 200
    assert res_step.json()["data"]["total_pasos"] >= 1

    # 3. Avanzar hasta el final
    res_end = api_client.post(
        f"/api/v1/laboratorio/corridas/{corrida_id}/avanzar/",
        {"modo": "RUN_TO_END", "max_pasos": 50},
        format="json",
    )
    assert res_end.status_code == 200
    assert res_end.json()["data"]["estado"] == "FINALIZADA"
    # Verificar salidas de texto
    salidas = res_end.json()["data"]["estado_vm"]["salidas_texto"]
    assert any("Resultado z = 30" in s for s in salidas)


@pytest.mark.django_db
def test_iniciar_corrida_con_snapshot_completo(api_client, monkeypatch):
    import uuid
    from apps.sistemas_expertos.models import SistemaExpertoModel
    se = SistemaExpertoModel.objects.create(nombre="SE Test Snapshot")
    mock_snapshot = {
        "sistema_experto_id": str(se.id),
        "base_conocimiento_id": str(uuid.uuid4()),
        "variables": [
            {"id": "v1", "nombre": "Fiebre", "tipo_dato": "BOOLEANO", "es_inicial": True},
            {"id": "v2", "nombre": "Diagnostico", "tipo_dato": "TEXTO", "es_inicial": False},
        ],
        "hechos_iniciales": [
            {"variable": "Fiebre", "valor": "true", "origen": "INICIAL"}
        ],
        "reglas": [
            {
                "id": "r-1",
                "nombre": "R1_Gripe",
                "orden": 0,
                "prioridad": 10,
                "marcada": False,
                "disparada": False,
                "premisas": [{"variable": "Fiebre", "operador": "=", "valor": "true"}],
                "conclusiones": [{"variable": "Diagnostico", "valor": "Gripe"}],
            }
        ],
    }

    from apps.laboratorio_algoritmos import views
    monkeypatch.setattr(views, "extraer_snapshot_base_conocimiento", lambda **kwargs: mock_snapshot)

    codigo = """
    void main(Lista<Regla> R, BaseHechos BH) {
        int n = R.length();
        int i = 0;
        while (i < n) {
            Regla r = R.get(i);
            if (!r.marcada) {
                Hecho nuevoHecho = Disparar(r, BH);
                if (nuevoHecho != null) {
                    BH.add(nuevoHecho);
                    Marcar(r);
                    println("Regla disparada: " + r.nombre + " -> " + nuevoHecho.variable + " = " + nuevoHecho.valor);
                }
            }
            i = i + 1;
        }
    }
    """

    res = api_client.post(
        "/api/v1/laboratorio/ejecutar/",
        {
            "sistema_experto_id": str(se.id),
            "codigo_fuente": codigo,
        },
        format="json",
    )
    assert res.status_code == 201
    data = res.json()["data"]
    corrida_id = data["id"]

    res_run = api_client.post(
        f"/api/v1/laboratorio/corridas/{corrida_id}/avanzar/",
        {"modo": "RUN_TO_END", "max_pasos": 100},
        format="json",
    )
    assert res_run.status_code == 200
    salidas = res_run.json()["data"]["estado_vm"]["salidas_texto"]
    assert any("Regla disparada: R1_Gripe -> Diagnostico = Gripe" in s for s in salidas)


@pytest.mark.django_db
def test_compartir_y_fork_programa(api_client, usuario):
    from django.contrib.auth import get_user_model
    from apps.actividades.models import CursoModel
    from apps.actividades.models_cursos import MatriculaCursoModel
    from apps.laboratorio_algoritmos.models import ProgramaAlgoritmoModel

    User = get_user_model()
    estudiante = User.objects.create_user(
        username="alumno_test",
        password="password123",
        email="alumno@test.com",
    )

    # 1. Docente crea curso
    curso = CursoModel.objects.create(
        codigo="INF-301",
        nombre="Inteligencia Artificial",
        docente=usuario,
    )
    # 2. Estudiante se matricula
    MatriculaCursoModel.objects.create(curso=curso, estudiante=estudiante, activo=True)

    # 3. Docente crea programa
    prog = ProgramaAlgoritmoModel.objects.create(
        owner=usuario,
        titulo="FWC Base del Docente",
        codigo_fuente="void main() { println(\"test\"); }",
    )

    # 4. Docente comparte programa al curso
    res_share = api_client.post(
        f"/api/v1/laboratorio/programas/{prog.id}/compartir/",
        {"curso_id": str(curso.id), "modo_acceso": "COPIA_EDICION"},
        format="json",
    )
    assert res_share.status_code == 201

    # 5. Estudiante lista compartidos
    api_client.force_authenticate(user=estudiante)
    res_list = api_client.get("/api/v1/laboratorio/programas/compartidos/")
    assert res_list.status_code == 200
    compartidos = res_list.json()["data"]
    assert len(compartidos) == 1
    assert compartidos[0]["programa_titulo"] == "FWC Base del Docente"
    assert compartidos[0]["modo_acceso"] == "COPIA_EDICION"

    # 6. Estudiante hace fork
    res_fork = api_client.post(
        f"/api/v1/laboratorio/programas/{prog.id}/fork/",
        {"titulo": "Mi Algoritmo Derivado"},
        format="json",
    )
    assert res_fork.status_code == 201
    fork_data = res_fork.json()["data"]
    assert fork_data["titulo"] == "Mi Algoritmo Derivado"
    assert fork_data["owner"] == estudiante.id
    assert fork_data["programa_origen"] == str(prog.id)


@pytest.mark.django_db
def test_ejecutar_y_avanzar_ejercicio_7_api(api_client, usuario):
    from apps.laboratorio_algoritmos.plantillas import EJERCICIOS_ALGORITMOS
    plantilla_ej7 = next(p for p in EJERCICIOS_ALGORITMOS if p["id"] == "ejercicio-7-consulta-previa")

    # Iniciar corrida con snapshot simulado
    payload = {
        "codigo_fuente": plantilla_ej7["codigo"],
        "snapshot_bc": {
            "variables": [
                {"id": "v_fieb", "nombre": "Fiebre", "tipo_dato": "TEXTO", "pregunta": "¿Tiene fiebre?"},
                {"id": "v_inf", "nombre": "Infeccion", "tipo_dato": "TEXTO"}
            ],
            "reglas": [
                {
                    "id": "r1",
                    "nombre": "R1",
                    "premisas": [
                        {"variable": "Fiebre", "variable_id": "v_fieb", "operador": "==", "valor": "Si", "tipo_dato": "TEXTO", "es_nativa": True}
                    ],
                    "conclusiones": [
                        {"variable": "Infeccion", "variable_id": "v_inf", "valor": "Si"}
                    ]
                }
            ],
            "hechos_iniciales": []
        }
    }
    res_inicio = api_client.post("/api/v1/laboratorio/ejecutar/", payload, format="json")
    assert res_inicio.status_code == 201, res_inicio.json()
    corrida_id = res_inicio.json()["data"]["id"]

    # Avanzar varias veces hasta llegar a la consulta
    res_avanzar = None
    for _ in range(35):
        res_avanzar = api_client.post(f"/api/v1/laboratorio/corridas/{corrida_id}/avanzar/", {"max_pasos": 1}, format="json")
        assert res_avanzar.status_code == 200, res_avanzar.json()
        if res_avanzar.json()["data"]["estado"] == "ESPERANDO_ENTRADA":
            break

    data_avanzar = res_avanzar.json()["data"]
    assert data_avanzar["estado"] == "ESPERANDO_ENTRADA"
    pregunta = data_avanzar["estado_vm"]["pregunta_pendiente"]
    assert pregunta is not None
    assert pregunta["variable_nombre"] == "Fiebre"

    # Responder la pregunta
    res_resp = api_client.post(
        f"/api/v1/laboratorio/corridas/{corrida_id}/responder/",
        {"valor": "Si", "cancelada": False},
        format="json"
    )
    assert res_resp.status_code == 200, res_resp.json()
    assert res_resp.json()["data"]["estado"] in ("EJECUTANDO", "FINALIZADA")




