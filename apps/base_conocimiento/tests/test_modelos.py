"""
Pruebas para los modelos ORM de Base de Conocimiento.
"""
import pytest
from django.db import IntegrityError
from apps.sistemas_expertos.models import SistemaExpertoModel
from apps.base_conocimiento.models import (
    BaseConocimientoModel,
    CondicionModel,
    ConclusionModel,
    HechoModel,
    ReglaModel,
    VariableModel,
)
from compartido.constantes.enums import OperadorCondicion, TipoDato


@pytest.fixture
def base_conocimiento_db(db):
    sistema = SistemaExpertoModel.objects.create(nombre="SE Test")
    return BaseConocimientoModel.objects.create(
        sistema_experto=sistema, nombre="BC Test", version=1
    )


@pytest.mark.django_db
def test_unicidad_nombre_hecho_en_misma_base(base_conocimiento_db):
    HechoModel.objects.create(
        base_conocimiento=base_conocimiento_db,
        nombre="hecho_1",
        tipo_dato=TipoDato.TEXTO.value,
    )
    with pytest.raises(IntegrityError):
        HechoModel.objects.create(
            base_conocimiento=base_conocimiento_db,
            nombre="hecho_1",
            tipo_dato=TipoDato.TEXTO.value,
        )


@pytest.mark.django_db
def test_unicidad_nombre_variable_en_misma_base(base_conocimiento_db):
    VariableModel.objects.create(
        base_conocimiento=base_conocimiento_db,
        nombre="var_1",
        tipo_dato=TipoDato.ENTERO.value,
    )
    with pytest.raises(IntegrityError):
        VariableModel.objects.create(
            base_conocimiento=base_conocimiento_db,
            nombre="var_1",
            tipo_dato=TipoDato.ENTERO.value,
        )


@pytest.mark.django_db
def test_unicidad_nombre_regla_en_misma_base(base_conocimiento_db):
    ReglaModel.objects.create(
        base_conocimiento=base_conocimiento_db,
        nombre="Regla_1",
        prioridad=5,
    )
    with pytest.raises(IntegrityError):
        ReglaModel.objects.create(
            base_conocimiento=base_conocimiento_db,
            nombre="Regla_1",
            prioridad=10,
        )


@pytest.mark.django_db
def test_creacion_condicion_y_conclusion(base_conocimiento_db):
    hecho = HechoModel.objects.create(
        base_conocimiento=base_conocimiento_db, nombre="h1", tipo_dato="BOOLEANO"
    )
    regla = ReglaModel.objects.create(
        base_conocimiento=base_conocimiento_db, nombre="r1", prioridad=1
    )

    cond = CondicionModel.objects.create(
        regla=regla,
        hecho=hecho,
        operador=OperadorCondicion.IGUAL.value,
        valor_esperado="true",
        orden=1,
    )
    assert cond.id is not None
    assert cond.regla_id == regla.id

    conc = ConclusionModel.objects.create(
        regla=regla,
        hecho_resultante=hecho,
        valor_resultante="true",
    )
    assert conc.id is not None
    assert conc.valor_resultante == "true"
