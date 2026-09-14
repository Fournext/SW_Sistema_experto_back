"""
Excepciones de dominio para el módulo de Base de Conocimiento.
"""
from compartido.excepciones.base import (
    ExcepcionEntidadNoEncontrada,
    ExcepcionValidacionDominio,
)


class BaseConocimientoNoEncontrada(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_base=None):
        if id_base:
            msg = f"Base de conocimiento no encontrada (ID: {id_base})"
        else:
            msg = "Base de conocimiento no encontrada."
        super().__init__(msg, {"base_conocimiento": [msg]})


class HechoNoEncontrado(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_hecho=None):
        msg = f"Hecho no encontrado (ID: {id_hecho})" if id_hecho else "Hecho no encontrado."
        super().__init__(msg, {"hecho": [msg]})


class HechoDuplicadoError(ExcepcionValidacionDominio):
    def __init__(self, nombre: str):
        super().__init__(
            f"Ya existe un hecho con el nombre '{nombre}' en esta base de conocimiento.",
            {"nombre": [f"El nombre '{nombre}' ya está en uso."]},
        )


class VariableNoEncontrada(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_variable=None):
        msg = f"Variable no encontrada (ID: {id_variable})" if id_variable else "Variable no encontrada."
        super().__init__(msg, {"variable": [msg]})


class VariableDuplicadaError(ExcepcionValidacionDominio):
    def __init__(self, nombre: str):
        super().__init__(
            f"Ya existe una variable con el nombre '{nombre}' en esta base de conocimiento.",
            {"nombre": [f"El nombre '{nombre}' ya está en uso."]},
        )


class ReglaNoEncontrada(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_regla=None):
        msg = f"Regla no encontrada (ID: {id_regla})" if id_regla else "Regla no encontrada."
        super().__init__(msg, {"regla": [msg]})


class ReglaDuplicadaError(ExcepcionValidacionDominio):
    def __init__(self, nombre: str):
        super().__init__(
            f"Ya existe una regla con el nombre '{nombre}' en esta base de conocimiento.",
            {"nombre": [f"El nombre '{nombre}' ya está en uso."]},
        )


class PrioridadInvalidaError(ExcepcionValidacionDominio):
    def __init__(self):
        super().__init__(
            "La prioridad de una regla debe ser un entero mayor o igual a cero.",
            {"prioridad": ["La prioridad debe ser >= 0."]},
        )


class FactorCertezaInvalidoError(ExcepcionValidacionDominio):
    def __init__(self):
        super().__init__(
            "El factor de certeza debe ser un número decimal entre 0 y 1.",
            {"factor_certeza": ["El factor de certeza debe estar entre 0.0 y 1.0."]},
        )


class CondicionNoEncontrada(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_condicion=None):
        msg = f"Condición no encontrada (ID: {id_condicion})" if id_condicion else "Condición no encontrada."
        super().__init__(msg, {"condicion": [msg]})


class CondicionReferenciaInvalidaError(ExcepcionValidacionDominio):
    def __init__(self):
        super().__init__(
            "Una condición debe referenciar exactamente una variable o un hecho, pero no ambos ni ninguno.",
            {"referencia": ["Debe especificar exactamente uno entre 'variable_id' y 'hecho_id'."]},
        )


class ConclusionNoEncontrada(ExcepcionEntidadNoEncontrada):
    def __init__(self, id_conclusion=None):
        msg = f"Conclusión no encontrada (ID: {id_conclusion})" if id_conclusion else "Conclusión no encontrada."
        super().__init__(msg, {"conclusion": [msg]})


class ConclusionReferenciaInvalidaError(ExcepcionValidacionDominio):
    def __init__(self):
        super().__init__(
            "Una conclusión debe afectar exactamente un hecho resultante o una variable resultante, "
            "pero no ambos ni ninguno.",
            {
                "destino": [
                    "Debe especificar exactamente uno entre 'hecho_resultante_id' y 'variable_resultante_id'."
                ]
            },
        )


class TipoDatoInvalidoError(ExcepcionValidacionDominio):
    def __init__(self, tipo: str):
        super().__init__(
            f"El tipo de dato '{tipo}' no es válido.",
            {"tipo_dato": ["Valores permitidos: TEXTO, ENTERO, DECIMAL, BOOLEANO."]},
        )
