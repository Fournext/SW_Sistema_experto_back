"""
Pruebas de modelos ORM para Sistemas Expertos.
"""
import pytest
from apps.sistemas_expertos.models import SistemaExpertoModel
from compartido.constantes.enums import EstadoSistema


@pytest.mark.django_db
def test_crear_modelo_sistema_experto():
    sistema = SistemaExpertoModel.objects.create(
        nombre="Sistema de Prueba",
        descripcion="Descripción de prueba",
        estado=EstadoSistema.BORRADOR.value,
    )
    assert sistema.id is not None
    assert sistema.nombre == "Sistema de Prueba"
    assert sistema.estado == "BORRADOR"
    assert sistema.creado_en is not None
    assert str(sistema) == "Sistema de Prueba (BORRADOR)"
