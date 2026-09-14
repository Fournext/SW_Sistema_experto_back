"""
Pruebas de modelos ORM para Editor Visual.
"""
from decimal import Decimal
from uuid import uuid4
import pytest
from django.db import IntegrityError
from apps.editor_visual.models import ConexionVisualModel, NodoVisualModel
from apps.sistemas_expertos.models import SistemaExpertoModel
from compartido.constantes.enums import TipoNodoVisual


@pytest.fixture
def sistema_db(db):
    return SistemaExpertoModel.objects.create(nombre="SE Editor Models")


@pytest.mark.django_db
def test_modelo_nodo_visual(sistema_db):
    nodo = NodoVisualModel.objects.create(
        sistema_experto=sistema_db,
        tipo=TipoNodoVisual.HECHO.value,
        referencia_id=uuid4(),
        posicion_x=Decimal("150.50"),
        posicion_y=Decimal("200.00"),
    )
    assert nodo.id is not None
    assert nodo.posicion_x == Decimal("150.50")


@pytest.mark.django_db
def test_conexion_duplicada_lanza_error_integridad(sistema_db):
    n1 = NodoVisualModel.objects.create(
        sistema_experto=sistema_db, tipo=TipoNodoVisual.HECHO.value, referencia_id=uuid4()
    )
    n2 = NodoVisualModel.objects.create(
        sistema_experto=sistema_db, tipo=TipoNodoVisual.REGLA.value, referencia_id=uuid4()
    )

    ConexionVisualModel.objects.create(
        sistema_experto=sistema_db, nodo_origen=n1, nodo_destino=n2
    )

    with pytest.raises(IntegrityError):
        ConexionVisualModel.objects.create(
            sistema_experto=sistema_db, nodo_origen=n1, nodo_destino=n2
        )
