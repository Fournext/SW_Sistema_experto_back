"""
Pruebas para los casos de uso de Sistemas Expertos.
"""
import pytest
from uuid import uuid4
from apps.sistemas_expertos.services import (
    CrearSistemaExperto,
    ActualizarSistemaExperto,
    ObtenerSistemaExperto,
    EliminarSistemaExperto,
)
from apps.sistemas_expertos.exceptions import (
    SistemaExpertoNoEncontrado,
    NombreSistemaExpertoRequerido,
)
from apps.base_conocimiento.models import BaseConocimientoModel
from compartido.constantes.enums import EstadoSistema


@pytest.mark.django_db
def test_crear_sistema_experto_exitoso_y_asocia_bc():
    caso_uso = CrearSistemaExperto()
    sistema = caso_uso.ejecutar(
        nombre="Sistema Médico",
        descripcion="Diagnóstico preliminar",
        estado=EstadoSistema.ACTIVO.value,
    )

    assert sistema.id is not None
    assert sistema.nombre == "Sistema Médico"
    assert sistema.estado == EstadoSistema.ACTIVO

    # Verifica que se crea automáticamente la Base de Conocimiento (1:1)
    bc = BaseConocimientoModel.objects.get(sistema_experto_id=sistema.id)
    assert bc is not None
    assert bc.version == 1


@pytest.mark.django_db
def test_crear_sistema_experto_nombre_obligatorio():
    caso_uso = CrearSistemaExperto()
    with pytest.raises(NombreSistemaExpertoRequerido):
        caso_uso.ejecutar(nombre="   ")


@pytest.mark.django_db
def test_actualizar_sistema_experto():
    crear = CrearSistemaExperto()
    sistema = crear.ejecutar(nombre="Original")

    actualizar = ActualizarSistemaExperto()
    actualizado = actualizar.ejecutar(
        id_sistema=sistema.id,
        nombre="Modificado",
        descripcion="Nueva desc",
        estado=EstadoSistema.ARCHIVADO.value,
    )

    assert actualizado.nombre == "Modificado"
    assert actualizado.descripcion == "Nueva desc"
    assert actualizado.estado == EstadoSistema.ARCHIVADO


@pytest.mark.django_db
def test_obtener_sistema_inexistente_lanza_error():
    obtener = ObtenerSistemaExperto()
    with pytest.raises(SistemaExpertoNoEncontrado):
        obtener.ejecutar(id_sistema=uuid4())


@pytest.mark.django_db
def test_eliminar_sistema_experto():
    crear = CrearSistemaExperto()
    sistema = crear.ejecutar(nombre="A Borrar")

    eliminar = EliminarSistemaExperto()
    eliminar.ejecutar(sistema.id)

    obtener = ObtenerSistemaExperto()
    with pytest.raises(SistemaExpertoNoEncontrado):
        obtener.ejecutar(sistema.id)
