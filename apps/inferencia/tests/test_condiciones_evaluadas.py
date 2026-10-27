from uuid import uuid4

import pytest

from apps.base_conocimiento.entities import Condicion, Regla
from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import AgregarCondicionARegla, CrearHecho, CrearRegla
from apps.inferencia.engine import MotorInferencia
from apps.inferencia.repositories import DjangoDetalleInferenciaRepositorio
from apps.inferencia.serializers import DetalleInferenciaSalidaSerializer, ReglaEvaluadaTrazaSerializer
from apps.inferencia.services import EjecutarInferencia, IniciarSimulacion, AvanzarPasoSimulacion
from apps.sistemas_expertos.services import CrearSistemaExperto
from compartido.constantes.enums import EstadoReglaInferencia


@pytest.mark.parametrize("individual", [False, True])
@pytest.mark.parametrize("valores", [[True, False, True], [True, True, True]])
def test_motor_registra_cada_condicion_sin_cortocircuito(individual, valores):
    ids = [uuid4() for _ in valores]
    condiciones = [Condicion(hecho_id=id_hecho, valor_esperado="true") for id_hecho in ids]
    regla = Regla(nombre="R1", condiciones=condiciones)
    parametros = {
        "memoria_trabajo": {str(i): valor for i, valor in zip(ids, valores)},
        "mapa_ids_a_nombres": {str(i): str(i) for i in ids},
        "numero_paso": 7,
    }
    motor = MotorInferencia()
    if individual:
        resultado = motor.ejecutar_un_paso_regla(regla=regla, **parametros)
    else:
        resultado = motor.ejecutar_un_paso(reglas=[regla], reglas_ejecutadas=set(), **parametros)

    esperado = [
        {"condicion_id": str(c.id), "resultado": valor}
        for c, valor in zip(condiciones, valores)
    ]
    estados = [t.estado for t in resultado.trazas_paso]
    assert estados == ([EstadoReglaInferencia.EVALUADA, EstadoReglaInferencia.ACTIVADA, EstadoReglaInferencia.EJECUTADA]
                       if all(valores) else [EstadoReglaInferencia.EVALUADA, EstadoReglaInferencia.RECHAZADA])
    for traza in resultado.trazas_paso:
        assert traza.condiciones_evaluadas == esperado
        assert traza.condiciones_cumplidas is all(valores)
        assert traza.paso_numero == 7
        assert ReglaEvaluadaTrazaSerializer(traza).data["condiciones_evaluadas"] == esperado
        assert ReglaEvaluadaTrazaSerializer(traza).data["paso_numero"] == 7


@pytest.mark.django_db
@pytest.mark.parametrize("simulacion", [False, True])
def test_persistir_y_consultar_resultados_individuales(simulacion):
    sistema = CrearSistemaExperto().ejecutar(nombre="Desglose de condiciones")
    base = BaseConocimientoModel.objects.get(sistema_experto_id=sistema.id)
    regla = CrearRegla().ejecutar(base_conocimiento_id=base.id, nombre="R1", prioridad=1, activa=True)
    esperado = []
    for index, valor in enumerate([True, False, True]):
        hecho = CrearHecho().ejecutar(base_conocimiento_id=base.id, nombre=f"h{index}",
                                     valor=str(valor).lower(), tipo_dato="BOOLEANO")
        condicion = AgregarCondicionARegla().ejecutar(regla_id=regla.id, hecho_id=hecho.id,
                                                   operador="=", valor_esperado="true", orden=index + 1)
        esperado.append({"condicion_id": str(condicion.id), "resultado": valor})

    if simulacion:
        ejecucion = IniciarSimulacion().ejecutar(sistema_experto_id=sistema.id)
        AvanzarPasoSimulacion().ejecutar(ejecucion.id)
        ejecucion_id = ejecucion.id
    else:
        resultado = EjecutarInferencia().ejecutar(sistema_experto_id=sistema.id)
        ejecucion_id = resultado.ejecucion_id

    repo = DjangoDetalleInferenciaRepositorio()
    detalles = repo.listar_por_ejecucion(ejecucion_id)
    assert len(detalles) == 2
    for detalle in detalles:
        assert detalle.condiciones_evaluadas == esperado
        assert DetalleInferenciaSalidaSerializer(detalle).data["condiciones_evaluadas"] == esperado
    # La actualización individual conserva el mismo desglose que el guardado en lote.
    assert repo.guardar(detalles[-1]).condiciones_evaluadas == esperado
