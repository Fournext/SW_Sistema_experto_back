"""
Excepciones base de dominio y sistema.
"""


class ExcepcionDominio(Exception):
    """Excepción base para cualquier error de la lógica de negocio/dominio."""
    def __init__(self, mensaje: str, errores: dict | list | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.errores = errores or {}


class ExcepcionEntidadNoEncontrada(ExcepcionDominio):
    """Lanzada cuando una entidad solicitada no existe."""
    pass


class ExcepcionValidacionDominio(ExcepcionDominio):
    """Lanzada cuando una regla de validación de negocio falla."""
    pass


class ExcepcionLimiteIteraciones(ExcepcionDominio):
    """Lanzada cuando el motor de inferencia alcanza el límite de iteraciones."""
    pass
