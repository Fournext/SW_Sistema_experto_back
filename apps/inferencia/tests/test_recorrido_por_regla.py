import pytest
from uuid import UUID

from apps.base_conocimiento.entities import Regla
from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import (
    AgregarConclusionARegla, AgregarCondicionARegla, CrearHecho, CrearRegla,
)
from apps.inferencia.models import DetalleInferenciaModel, PasoInferenciaModel
from apps.inferencia.exceptions import LimiteIteracionesAlcanzado
from apps.inferencia.repositories import DjangoEjecucionInferenciaRepositorio
from apps.inferencia.recorrido import cerrar_vuelta, nuevo_recorrido, ordenar_reglas
from apps.inferencia.services import AvanzarPasoSimulacion, ControlarSimulacion, IniciarSimulacion
from apps.sistemas_expertos.services import CrearSistemaExperto


def test_orden_estable_usa_uuid_ante_empate_de_prioridad_y_nombre():
    primera = Regla(id=UUID(int=1), nombre="R", prioridad=10)
    segunda = Regla(id=UUID(int=2), nombre="R", prioridad=10)
    assert ordenar_reglas([segunda, primera]) == [primera, segunda]


def test_vuelta_sin_disparos_finaliza_aunque_haya_entradas_externas_nuevas():
    regla = Regla(nombre="Pendiente")
    recorrido = nuevo_recorrido({"entrada": False})
    recorrido["visitadas"] = [str(regla.id)]
    estado, finalizada = cerrar_vuelta(recorrido, {"entrada": True}, [regla], set())
    assert finalizada is True
    assert estado["numero_vuelta"] == 1


@pytest.fixture
def fabrica_recorrido(db):
    sistema = CrearSistemaExperto().ejecutar(nombre="Recorrido persistente")
    base = BaseConocimientoModel.objects.get(sistema_experto_id=sistema.id)

    def hecho(nombre, valor="false"):
        return CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre=nombre, valor=valor, tipo_dato="BOOLEANO")

    def regla(nombre, prioridad, entrada, salida=None):
        creada = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre=nombre, prioridad=prioridad, activa=True)
        AgregarCondicionARegla().ejecutar(regla_id=creada.id, hecho_id=entrada.id,
                                       operador="=", valor_esperado="true")
        if salida is not None:
            AgregarConclusionARegla().ejecutar(regla_id=creada.id, hecho_resultante_id=salida.id, valor_resultante="true")
        return creada

    return sistema, hecho, regla


def _leer(api_client, sesion):
    respuesta = api_client.get(f"/api/v1/inferencias/{sesion.id}/")
    assert respuesta.status_code == 200
    return respuesta.json()["data"]


def _siguiente(api_client, sesion):
    return _leer(api_client, sesion)["siguiente_regla"]


def _avanzar(sesion, pequeno=True):
    return AvanzarPasoSimulacion().ejecutar(sesion.id, modo_evaluacion="POR_REGLA" if pequeno else None)


def _evaluada(sesion):
    paso = PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id).order_by("-numero_paso").first()
    detalles = DetalleInferenciaModel.objects.filter(ejecucion_id=sesion.id, paso_numero=paso.numero_paso,
                                                   estado_regla="EVALUADA")
    return list(detalles.values_list("regla_id", flat=True))


@pytest.mark.django_db
def test_por_regla_continua_despues_de_disparar_y_reconsidera_rechazada_en_nueva_vuelta(api_client, fabrica_recorrido):
    sistema, hecho, regla = fabrica_recorrido
    inicio = hecho("inicio", "true")
    habilitado = hecho("habilitado")
    final = hecho("final")
    extra = hecho("extra")
    primera = regla("R1 depende", 30, habilitado, final)
    segunda = regla("R2 habilita", 20, inicio, habilitado)
    tercera = regla("R3 posterior", 10, inicio, extra)
    sesion = IniciarSimulacion().ejecutar(sistema.id)

    _avanzar(sesion)
    assert _evaluada(sesion) == [primera.id]
    assert _siguiente(api_client, sesion)["id"] == str(segunda.id)
    _avanzar(sesion)
    assert _evaluada(sesion) == [segunda.id]
    assert _siguiente(api_client, sesion)["id"] == str(tercera.id)
    assert _leer(api_client, sesion)["numero_vuelta"] == 1
    _avanzar(sesion)
    assert _evaluada(sesion) == [tercera.id]
    progreso = _leer(api_client, sesion)
    assert progreso["numero_vuelta"] == 2
    assert progreso["siguiente_regla"]["id"] == str(primera.id)

    resultado = _avanzar(sesion)
    assert resultado["finalizado"] is True
    assert _evaluada(sesion) == [primera.id]
    assert _siguiente(api_client, sesion) is None
    assert list(PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id, regla_disparada_id=primera.id)
                .values_list("numero_paso", flat=True)) == [4]


@pytest.mark.django_db
def test_fin_de_vuelta_sin_cambio_en_bh_no_repite_rechazadas(api_client, fabrica_recorrido):
    sistema, hecho, regla = fabrica_recorrido
    inicio = hecho("inicio", "true")
    falso = hecho("falso")
    primera = regla("R1 rechazada", 20, falso)
    segunda = regla("R2 sin cambio", 10, inicio, inicio)
    sesion = IniciarSimulacion().ejecutar(sistema.id)
    _avanzar(sesion)
    assert _evaluada(sesion) == [primera.id]
    resultado = _avanzar(sesion)
    assert _evaluada(sesion) == [segunda.id]
    assert resultado["finalizado"] is True
    progreso = _leer(api_client, sesion)
    assert progreso["numero_vuelta"] == 1
    assert progreso["siguiente_regla"] is None
    assert PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id).count() == 2


@pytest.mark.django_db
def test_avance_grande_no_mueve_cursor_pequeno_y_sus_disparos_cuentan_para_la_vuelta(api_client, fabrica_recorrido):
    sistema, hecho, regla = fabrica_recorrido
    inicio = hecho("inicio", "true")
    falso = hecho("falso")
    salida = hecho("salida")
    primera = regla("R1 rechazada", 30, falso)
    segunda = regla("R2 activable", 20, inicio, salida)
    tercera = regla("R3 rechazada", 10, falso)
    sesion = IniciarSimulacion().ejecutar(sistema.id)
    _avanzar(sesion)
    _avanzar(sesion, pequeno=False)
    guardada = DjangoEjecucionInferenciaRepositorio().obtener_por_id(sesion.id)
    assert guardada.recorrido_por_regla["visitadas"] == [str(primera.id)]
    assert guardada.recorrido_por_regla["hubo_disparo"] is True
    assert _siguiente(api_client, sesion)["id"] == str(tercera.id)
    assert PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id, regla_disparada_id=segunda.id).count() == 1
    _avanzar(sesion)
    progreso = _leer(api_client, sesion)
    assert progreso["numero_vuelta"] == 2
    assert progreso["siguiente_regla"]["id"] == str(primera.id)
    _avanzar(sesion)
    assert _siguiente(api_client, sesion)["id"] == str(tercera.id)
    assert _avanzar(sesion)["finalizado"] is True
    assert PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id, regla_disparada_id=segunda.id).count() == 1


@pytest.mark.django_db
def test_inicio_lectura_pausa_y_reinicio_publican_y_conservan_progreso(api_client, fabrica_recorrido):
    sistema, hecho, regla = fabrica_recorrido
    falso = hecho("falso")
    regla("Zeta", 5, falso)
    beta = regla("Beta", 20, falso)
    alfa = regla("Alfa", 20, falso)
    respuesta = api_client.post(f"/api/v1/sistemas-expertos/{sistema.id}/simulaciones/", {}, format="json")
    assert respuesta.status_code == 201
    data = respuesta.json()["data"]
    assert data["numero_vuelta"] == 1
    assert data["siguiente_regla"] == {"id": str(alfa.id), "nombre": "Alfa", "prioridad": 20}
    sesion = DjangoEjecucionInferenciaRepositorio().obtener_por_id(data["id"])
    respuesta = api_client.post(f"/api/v1/simulaciones/{sesion.id}/paso/", {"modo_evaluacion": "POR_REGLA"}, format="json")
    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["siguiente_regla"]["id"] == str(beta.id)
    ControlarSimulacion().pausar(sesion.id)
    assert _leer(api_client, sesion)["estado"] == "PAUSADA"
    assert _siguiente(api_client, sesion)["id"] == str(beta.id)
    persistida = DjangoEjecucionInferenciaRepositorio().obtener_por_id(sesion.id)
    assert persistida.recorrido_por_regla["visitadas"] == [str(alfa.id)]
    ControlarSimulacion().continuar(sesion.id)
    assert PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id).count() == 1
    assert _leer(api_client, sesion)["estado"] == "EJECUTANDO"
    assert _siguiente(api_client, sesion)["id"] == str(beta.id)
    ControlarSimulacion().reiniciar(sesion.id)
    progreso = _leer(api_client, sesion)
    assert progreso["paso_actual"] == 0
    assert progreso["numero_vuelta"] == 1
    assert progreso["siguiente_regla"]["id"] == str(alfa.id)
    assert not PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id).exists()
    persistida = DjangoEjecucionInferenciaRepositorio().obtener_por_id(sesion.id)
    assert persistida.recorrido_por_regla["visitadas"] == []
    assert persistida.recorrido_por_regla["hubo_disparo"] is False


@pytest.mark.django_db
def test_grande_que_dispara_ultima_pendiente_prepara_nueva_vuelta_sin_click_vacio(api_client, fabrica_recorrido):
    sistema, hecho, regla = fabrica_recorrido
    inicio = hecho("inicio", "true")
    habilitado = hecho("habilitado")
    salida = hecho("salida")
    primera = regla("R1 depende", 20, habilitado, salida)
    segunda = regla("R2 habilita", 10, inicio, habilitado)
    sesion = IniciarSimulacion().ejecutar(sistema.id)
    _avanzar(sesion)
    assert _siguiente(api_client, sesion)["id"] == str(segunda.id)
    resultado = _avanzar(sesion, pequeno=False)
    assert resultado["finalizado"] is False
    progreso = _leer(api_client, sesion)
    assert progreso["numero_vuelta"] == 2
    assert progreso["siguiente_regla"]["id"] == str(primera.id)
    assert PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id).count() == 2
    assert _avanzar(sesion)["finalizado"] is True
    assert _evaluada(sesion) == [primera.id]
    assert PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id).count() == 3


@pytest.mark.django_db
def test_limite_de_vueltas_no_persiste_un_paso_adicional(settings, fabrica_recorrido):
    settings.MAX_INFERENCE_ITERATIONS = 1
    sistema, hecho, regla = fabrica_recorrido
    inicio = hecho("inicio", "true")
    habilitado = hecho("habilitado")
    regla("R1 depende", 20, habilitado)
    regla("R2 habilita", 10, inicio, habilitado)
    sesion = IniciarSimulacion().ejecutar(sistema.id)
    _avanzar(sesion)
    _avanzar(sesion)
    with pytest.raises(LimiteIteracionesAlcanzado):
        _avanzar(sesion)
    assert PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id).count() == 2
    assert DjangoEjecucionInferenciaRepositorio().obtener_por_id(sesion.id).paso_actual == 2


def _avanzar_api(api_client, sesion, pequeno=True):
    datos = {"modo_evaluacion": "POR_REGLA"} if pequeno else {}
    respuesta = api_client.post(f"/api/v1/simulaciones/{sesion.id}/paso/", datos, format="json")
    assert respuesta.status_code == 200
    return respuesta.json()["data"]


def _grupos_visuales_por_paso(sesion):
    grupos = {}
    for detalle in DetalleInferenciaModel.objects.filter(ejecucion_id=sesion.id).order_by("orden"):
        grupos.setdefault(detalle.paso_numero, set()).add(detalle.paso_visual)
    return grupos


@pytest.mark.django_db
def test_tres_clicks_pequenos_comparten_paso_visual_sin_alterar_ledger_fisico(api_client, fabrica_recorrido):
    sistema, hecho, regla = fabrica_recorrido
    falso = hecho("falso")
    for indice in range(3):
        regla(f"R{indice}", 30 - indice, falso)
    respuesta = api_client.post(f"/api/v1/sistemas-expertos/{sistema.id}/simulaciones/", {}, format="json")
    assert respuesta.status_code == 201
    assert respuesta.json()["data"]["paso_visual_actual"] == 0
    sesion = DjangoEjecucionInferenciaRepositorio().obtener_por_id(respuesta.json()["data"]["id"])
    for paso_fisico in range(1, 4):
        datos = _avanzar_api(api_client, sesion)
        assert datos["paso_actual"] == paso_fisico
        assert datos["paso_visual_actual"] == 1
        assert _leer(api_client, sesion)["paso_visual_actual"] == 1
    assert datos["finalizado"] is True
    assert _grupos_visuales_por_paso(sesion) == {1: {1}, 2: {1}, 3: {1}}
    assert list(PasoInferenciaModel.objects.filter(ejecucion_id=sesion.id).order_by("numero_paso")
                .values_list("numero_paso", flat=True)) == [1, 2, 3]
    respuesta = api_client.get(f"/api/v1/inferencias/{sesion.id}/detalles/")
    assert respuesta.status_code == 200
    assert {d["paso_visual"] for d in respuesta.json()["data"]} == {1}
    assert {d["paso_numero"] for d in respuesta.json()["data"]} == {1, 2, 3}


@pytest.mark.django_db
def test_nueva_vuelta_abre_otro_paso_visual_para_reconsiderar_regla(api_client, fabrica_recorrido):
    sistema, hecho, regla = fabrica_recorrido
    inicio = hecho("inicio", "true")
    habilitado = hecho("habilitado")
    salida = hecho("salida")
    regla("R1 depende", 20, habilitado, salida)
    regla("R2 habilita", 10, inicio, habilitado)
    sesion = IniciarSimulacion().ejecutar(sistema.id)
    assert _avanzar_api(api_client, sesion)["paso_visual_actual"] == 1
    segunda = _avanzar_api(api_client, sesion)
    assert segunda["numero_vuelta"] == 2
    assert segunda["paso_visual_actual"] == 1
    tercera = _avanzar_api(api_client, sesion)
    assert tercera["paso_actual"] == 3
    assert tercera["paso_visual_actual"] == 2
    assert tercera["finalizado"] is True
    assert _grupos_visuales_por_paso(sesion) == {1: {1}, 2: {1}, 3: {2}}


@pytest.mark.django_db
def test_grande_tiene_grupo_propio_y_pequeno_retoma_su_grupo_hasta_cerrar_vuelta(api_client, fabrica_recorrido):
    sistema, hecho, regla = fabrica_recorrido
    inicio = hecho("inicio", "true")
    falso = hecho("falso")
    salida = hecho("salida")
    regla("R1 rechazada", 30, falso)
    regla("R2 activable", 20, inicio, salida)
    regla("R3 rechazada", 10, falso)
    sesion = IniciarSimulacion().ejecutar(sistema.id)
    assert _avanzar_api(api_client, sesion)["paso_visual_actual"] == 1


    assert _avanzar_api(api_client, sesion, pequeno=False)["paso_visual_actual"] == 2
    for accion in ("PAUSAR", "CONTINUAR"):
        respuesta = api_client.post(f"/api/v1/simulaciones/{sesion.id}/control/", {"accion": accion}, format="json")
        assert respuesta.status_code == 200
        assert respuesta.json()["data"]["paso_visual_actual"] == 2
        assert respuesta.json()["data"]["paso_actual"] == 2
    tercera = _avanzar_api(api_client, sesion)
    assert tercera["paso_visual_actual"] == 1
    assert tercera["numero_vuelta"] == 2
    assert _leer(api_client, sesion)["paso_visual_actual"] == 1
    assert _avanzar_api(api_client, sesion)["paso_visual_actual"] == 3
    assert _avanzar_api(api_client, sesion)["paso_visual_actual"] == 3
    assert _grupos_visuales_por_paso(sesion) == {1: {1}, 2: {2}, 3: {1}, 4: {3}, 5: {3}}
    respuesta = api_client.post(f"/api/v1/simulaciones/{sesion.id}/control/", {"accion": "REINICIAR"}, format="json")
    assert respuesta.status_code == 200
    assert respuesta.json()["data"]["paso_visual_actual"] == 0
    assert respuesta.json()["data"]["paso_actual"] == 0
    assert not DetalleInferenciaModel.objects.filter(ejecucion_id=sesion.id).exists()
    assert _avanzar_api(api_client, sesion)["paso_visual_actual"] == 1


@pytest.mark.django_db
def test_sesion_antigua_asigna_grupo_nuevo_sin_colisionar_con_pasos_fisicos_previos(api_client, fabrica_recorrido):
    sistema, hecho, regla = fabrica_recorrido
    falso = hecho("falso")
    for indice in range(3):
        regla(f"R{indice}", 30 - indice, falso)
    sesion = IniciarSimulacion().ejecutar(sistema.id)
    _avanzar_api(api_client, sesion)
    _avanzar_api(api_client, sesion)
    repo = DjangoEjecucionInferenciaRepositorio()
    antigua = repo.obtener_por_id(sesion.id)
    for clave in ("contador_visual", "grupo_pequeno", "paso_visual_actual"):
        antigua.recorrido_por_regla.pop(clave, None)
    repo.guardar(antigua)
    DetalleInferenciaModel.objects.filter(ejecucion_id=sesion.id).update(paso_visual=None)
    respuesta = _avanzar_api(api_client, sesion)
    assert respuesta["paso_actual"] == 3
    assert respuesta["paso_visual_actual"] == 3
    assert _grupos_visuales_por_paso(sesion) == {1: {None}, 2: {None}, 3: {3}}
