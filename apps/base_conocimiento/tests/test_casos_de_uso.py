"""
Pruebas de casos de uso para Base de Conocimiento.
"""
from decimal import Decimal
import pytest
from apps.base_conocimiento.exceptions import (
    ConclusionReferenciaInvalidaError,
    CondicionReferenciaInvalidaError,
    FactorCertezaInvalidoError,
    HechoDuplicadoError,
    PrioridadInvalidaError,
    TipoDatoInvalidoError,
    VariableDuplicadaError,
)
from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import (
    AgregarConclusionARegla,
    AgregarCondicionARegla,
    CrearHecho,
    CrearRegla,
    CrearVariable,
)
from apps.sistemas_expertos.services import CrearSistemaExperto


@pytest.fixture
def bc_id(db):
    se = CrearSistemaExperto().ejecutar(nombre="SE BC Test")
    bc = BaseConocimientoModel.objects.get(sistema_experto_id=se.id)
    return bc.id


@pytest.mark.django_db
def test_crear_hecho_duplicado_lanza_error(bc_id):
    caso_uso = CrearHecho()
    caso_uso.ejecutar(base_conocimiento_id=bc_id, nombre="lluvia", valor="true")

    with pytest.raises(HechoDuplicadoError):
        caso_uso.ejecutar(base_conocimiento_id=bc_id, nombre="lluvia", valor="false")


@pytest.mark.django_db
def test_validar_tipo_dato_hecho_invalido(bc_id):
    caso_uso = CrearHecho()
    with pytest.raises(TipoDatoInvalidoError):
        caso_uso.ejecutar(base_conocimiento_id=bc_id, nombre="test", tipo_dato="DESCONOCIDO")


@pytest.mark.django_db
def test_crear_variable_duplicada_lanza_error(bc_id):
    caso_uso = CrearVariable()
    caso_uso.ejecutar(base_conocimiento_id=bc_id, nombre="temperatura")

    with pytest.raises(VariableDuplicadaError):
        caso_uso.ejecutar(base_conocimiento_id=bc_id, nombre="temperatura")


@pytest.mark.django_db
def test_validar_prioridad_negativa_regla(bc_id):
    caso_uso = CrearRegla()
    with pytest.raises(PrioridadInvalidaError):
        caso_uso.ejecutar(base_conocimiento_id=bc_id, nombre="ReglaNeg", prioridad=-5)


@pytest.mark.django_db
def test_validar_factor_certeza_fuera_de_rango(bc_id):
    caso_uso = CrearRegla()
    with pytest.raises(FactorCertezaInvalidoError):
        caso_uso.ejecutar(
            base_conocimiento_id=bc_id, nombre="ReglaFC", factor_certeza=Decimal("1.5")
        )


@pytest.mark.django_db
def test_condicion_referencia_exclusiva(bc_id):
    regla = CrearRegla().ejecutar(base_conocimiento_id=bc_id, nombre="ReglaCond")
    hecho = CrearHecho().ejecutar(base_conocimiento_id=bc_id, nombre="hecho_cond")
    variable = CrearVariable().ejecutar(base_conocimiento_id=bc_id, nombre="var_cond")

    caso_cond = AgregarCondicionARegla()

    # Error si se envían AMBOS (hecho_id y variable_id)
    with pytest.raises(CondicionReferenciaInvalidaError):
        caso_cond.ejecutar(
            regla_id=regla.id,
            operador="=",
            valor_esperado="x",
            variable_id=variable.id,
            hecho_id=hecho.id,
        )

    # Error si no se envía NINGUNO
    with pytest.raises(CondicionReferenciaInvalidaError):
        caso_cond.ejecutar(
            regla_id=regla.id,
            operador="=",
            valor_esperado="x",
            variable_id=None,
            hecho_id=None,
        )


@pytest.mark.django_db
def test_conclusion_destino_exclusivo(bc_id):
    regla = CrearRegla().ejecutar(base_conocimiento_id=bc_id, nombre="ReglaConc")
    hecho = CrearHecho().ejecutar(base_conocimiento_id=bc_id, nombre="hecho_conc")
    variable = CrearVariable().ejecutar(base_conocimiento_id=bc_id, nombre="var_conc")

    caso_conc = AgregarConclusionARegla()

    # Error si se envían AMBOS
    with pytest.raises(ConclusionReferenciaInvalidaError):
        caso_conc.ejecutar(
            regla_id=regla.id,
            valor_resultante="res",
            hecho_resultante_id=hecho.id,
            variable_resultante_id=variable.id,
        )

    # Error si no se envía NINGUNO
    with pytest.raises(ConclusionReferenciaInvalidaError):
        caso_conc.ejecutar(
            regla_id=regla.id,
            valor_resultante="res",
            hecho_resultante_id=None,
            variable_resultante_id=None,
        )
