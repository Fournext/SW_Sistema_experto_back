"""
Pruebas para los casos de uso del Editor Visual.
"""
from decimal import Decimal
from uuid import uuid4
import pytest
from apps.base_conocimiento.models import BaseConocimientoModel
from apps.base_conocimiento.services import CrearHecho
from apps.editor_visual.exceptions import (
    ConexionConsigoMismoError,
    ConexionDuplicadaError,
    NodosDistintoSistemaError,
    ReferenciaInvalidaError,
)
from apps.editor_visual.services import (
    CrearConexionVisual,
    CrearNodoVisual,
    MoverNodoVisual,
)
from apps.sistemas_expertos.services import CrearSistemaExperto
from compartido.constantes.enums import TipoNodoVisual


@pytest.fixture
def setup_editor(db):
    se = CrearSistemaExperto().ejecutar(nombre="SE Editor Casos")
    bc = BaseConocimientoModel.objects.get(sistema_experto_id=se.id)
    hecho = CrearHecho().ejecutar(
        base_conocimiento_id=bc.id, nombre="h_visual", valor="1"
    )
    return {"se": se, "bc": bc, "hecho": hecho}


@pytest.mark.django_db
def test_crear_nodo_visual_exitoso(setup_editor):
    se = setup_editor["se"]
    hecho = setup_editor["hecho"]

    caso_nodo = CrearNodoVisual()
    nodo = caso_nodo.ejecutar(
        sistema_experto_id=se.id,
        tipo=TipoNodoVisual.HECHO.value,
        referencia_id=hecho.id,
        posicion_x=Decimal("50.0"),
        posicion_y=Decimal("100.0"),
    )
    assert nodo.id is not None
    assert nodo.referencia_id == hecho.id


@pytest.mark.django_db
def test_crear_nodo_visual_referencia_inexistente(setup_editor):
    se = setup_editor["se"]
    caso_nodo = CrearNodoVisual()
    with pytest.raises(ReferenciaInvalidaError):
        caso_nodo.ejecutar(
            sistema_experto_id=se.id,
            tipo=TipoNodoVisual.HECHO.value,
            referencia_id=uuid4(),
        )


@pytest.mark.django_db
def test_mover_nodo_visual(setup_editor):
    se = setup_editor["se"]
    hecho = setup_editor["hecho"]
    nodo = CrearNodoVisual().ejecutar(
        sistema_experto_id=se.id,
        tipo=TipoNodoVisual.HECHO.value,
        referencia_id=hecho.id,
    )

    mover = MoverNodoVisual()
    nodo_movido = mover.ejecutar(
        id_nodo=nodo.id, posicion_x=Decimal("300.0"), posicion_y=Decimal("400.0")
    )
    assert nodo_movido.posicion_x == Decimal("300.0")
    assert nodo_movido.posicion_y == Decimal("400.0")


@pytest.mark.django_db
def test_conexion_consigo_mismo_falla(setup_editor):
    se = setup_editor["se"]
    hecho = setup_editor["hecho"]
    nodo = CrearNodoVisual().ejecutar(
        sistema_experto_id=se.id,
        tipo=TipoNodoVisual.HECHO.value,
        referencia_id=hecho.id,
    )

    caso_con = CrearConexionVisual()
    with pytest.raises(ConexionConsigoMismoError):
        caso_con.ejecutar(
            sistema_experto_id=se.id,
            nodo_origen_id=nodo.id,
            nodo_destino_id=nodo.id,
        )


@pytest.mark.django_db
def test_conexion_distinto_sistema_falla(setup_editor):
    se1 = setup_editor["se"]
    hecho1 = setup_editor["hecho"]

    se2 = CrearSistemaExperto().ejecutar(nombre="SE 2")
    bc2 = BaseConocimientoModel.objects.get(sistema_experto_id=se2.id)
    hecho2 = CrearHecho().ejecutar(base_conocimiento_id=bc2.id, nombre="h_se2")

    n1 = CrearNodoVisual().ejecutar(
        sistema_experto_id=se1.id, tipo="HECHO", referencia_id=hecho1.id
    )
    n2 = CrearNodoVisual().ejecutar(
        sistema_experto_id=se2.id, tipo="HECHO", referencia_id=hecho2.id
    )

    caso_con = CrearConexionVisual()
    with pytest.raises(NodosDistintoSistemaError):
        caso_con.ejecutar(
            sistema_experto_id=se1.id,
            nodo_origen_id=n1.id,
            nodo_destino_id=n2.id,
        )


@pytest.mark.django_db
def test_conexion_duplicada_falla(setup_editor):
    se = setup_editor["se"]
    bc = setup_editor["bc"]
    h1 = setup_editor["hecho"]
    h2 = CrearHecho().ejecutar(base_conocimiento_id=bc.id, nombre="h_otro")

    n1 = CrearNodoVisual().ejecutar(
        sistema_experto_id=se.id, tipo="HECHO", referencia_id=h1.id
    )
    n2 = CrearNodoVisual().ejecutar(
        sistema_experto_id=se.id, tipo="HECHO", referencia_id=h2.id
    )

    caso_con = CrearConexionVisual()
    caso_con.ejecutar(
        sistema_experto_id=se.id, nodo_origen_id=n1.id, nodo_destino_id=n2.id
    )

    with pytest.raises(ConexionDuplicadaError):
        caso_con.ejecutar(
            sistema_experto_id=se.id, nodo_origen_id=n1.id, nodo_destino_id=n2.id
        )
