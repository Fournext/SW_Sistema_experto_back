"""Módulo de excepciones."""
from .base import (
    ExcepcionDominio,
    ExcepcionEntidadNoEncontrada,
    ExcepcionValidacionDominio,
    ExcepcionLimiteIteraciones,
)
from .manejadores import manejador_excepciones_global

__all__ = [
    "ExcepcionDominio",
    "ExcepcionEntidadNoEncontrada",
    "ExcepcionValidacionDominio",
    "ExcepcionLimiteIteraciones",
    "manejador_excepciones_global",
]
