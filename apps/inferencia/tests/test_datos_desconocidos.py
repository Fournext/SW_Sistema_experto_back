from uuid import uuid4

import pytest

from apps.base_conocimiento.entities import Condicion, Conclusion, Hecho, Regla
from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import AgregarConclusionARegla, AgregarCondicionARegla, CrearHecho, CrearRegla
from apps.inferencia.engine import MotorInferencia
from apps.inferencia.evaluator import EvaluadorCondicion
from apps.inferencia.services import AvanzarPasoSimulacion, ControlarSimulacion, IniciarSimulacion
from apps.inferencia.repositories import DjangoEjecucionInferenciaRepositorio
from apps.sistemas_expertos.services import CrearSistemaExperto


@pytest.mark.parametrize("tipo", ["TEXTO", "ENTERO", "DECIMAL", "BOOLEANO", "OPCION"])
@pytest.mark.parametrize("valor", [None, "", "   "])
def test_dato_inicial_desconocido_no_entra_en_bh_ni_dispara_desigualdad(tipo, valor):
    dato = Hecho(nombre="entrada", valor=valor, tipo_dato=tipo)
    condicion = Condicion(hecho_id=dato.id, operador="!=", valor_esperado="true" if tipo == "BOOLEANO" else "x")
    regla = Regla(nombre="R1", condiciones=[condicion], conclusiones=[Conclusion(valor_resultante="incorrecto")])
    resultado = MotorInferencia().ejecutar([dato], [regla])
    assert resultado.conclusion_final is None
    assert resultado.hechos_generados == []
    assert "entrada" not in resultado.pasos[0].memoria_trabajo_pre
    assert "entrada" not in resultado.pasos[0].memoria_trabajo_post
    assert MotorInferencia._parsear_valor_hecho(valor, tipo) is None


@pytest.mark.parametrize("valor", [None, "", "  "])
def test_evaluador_rechaza_valor_desconocido_incluso_si_existe_clave(valor):
    id_hecho = uuid4()
    for operador in ["=", "!=", ">", "<", "CONTIENE"]:
        for esperado in ["false", "0", "texto"]:
            condicion = Condicion(hecho_id=id_hecho, operador=operador, valor_esperado=esperado)
            assert EvaluadorCondicion.evaluar(condicion, {"entrada": valor}, {str(id_hecho): "entrada"}) is False


@pytest.mark.parametrize("tipo,valor,esperado", [("BOOLEANO", False, "false"), ("ENTERO", 0, "0"), ("DECIMAL", 0.0, "0")])
def test_false_y_cero_si_son_datos_conocidos_y_pueden_disparar(tipo, valor, esperado):
    dato = Hecho(nombre="entrada", valor=valor, tipo_dato=tipo)
    regla = Regla(nombre="R1", condiciones=[Condicion(hecho_id=dato.id, valor_esperado=esperado)],
                  conclusiones=[Conclusion(valor_resultante="correcto")])
    resultado = MotorInferencia().ejecutar([dato], [regla])
    assert resultado.conclusion_final == "correcto"
    assert resultado.pasos[0].memoria_trabajo_pre["entrada"] == valor


@pytest.mark.django_db
def test_simulacion_excluye_ausentes_al_iniciar_responder_y_reiniciar():
    sistema = CrearSistemaExperto().ejecutar(nombre="Simulación sin dato")
    base = BaseConocimientoModel.objects.get(sistema_experto_id=sistema.id)
    entrada = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="entrada", valor=None, tipo_dato="BOOLEANO")
    cero = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="cero", valor="0", tipo_dato="ENTERO")
    falso = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre="falso", valor="false", tipo_dato="BOOLEANO")
    regla = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="R1", prioridad=1)
    AgregarCondicionARegla().ejecutar(regla_id=regla.id, hecho_id=entrada.id, operador="!=", valor_esperado="true")
    AgregarConclusionARegla().ejecutar(regla_id=regla.id, hecho_resultante_id=cero.id, valor_resultante="9")
    sesion = IniciarSimulacion().ejecutar(sistema.id)
    assert sesion.memoria_trabajo_snapshot == {"cero": 0, "falso": False}
    avance = AvanzarPasoSimulacion().ejecutar(sesion.id, hechos_nuevos=[{"nombre": "entrada", "valor": "", "tipo_dato": "BOOLEANO"}])
    assert avance["hechos_generados"] == []
    assert avance["memoria_trabajo"] == {"cero": 0, "falso": False}
    reinicio = ControlarSimulacion().reiniciar(sesion.id)
    assert reinicio.memoria_trabajo_snapshot == {"cero": 0, "falso": False}
    personalizada = IniciarSimulacion().ejecutar(sistema.id, hechos_iniciales_custom=[
        {"nombre": "entrada", "valor": "", "tipo_dato": "BOOLEANO"},
        {"nombre": "cero", "valor": 0, "tipo_dato": "ENTERO"},
        {"nombre": "falso", "valor": False, "tipo_dato": "BOOLEANO"},
    ])
    assert personalizada.memoria_trabajo_snapshot == {"cero": 0, "falso": False}
    assert DjangoEjecucionInferenciaRepositorio().obtener_por_id(personalizada.id).memoria_trabajo_snapshot == {"cero": 0, "falso": False}
