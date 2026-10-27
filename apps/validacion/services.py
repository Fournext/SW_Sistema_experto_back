"""
Servicios y casos de uso para la Validación de Bases de Conocimiento (Sprint 2 - HU-18, HU-19).
"""
from typing import List, Optional
from uuid import UUID
from django.db import transaction

from apps.base_conocimiento.exceptions import BaseConocimientoNoEncontrada
from apps.base_conocimiento.repositories import (
    BaseConocimientoRepositorio,
    DjangoBaseConocimientoRepositorio,
    DjangoHechoRepositorio,
    DjangoReglaRepositorio,
    DjangoVariableRepositorio,
    HechoRepositorio,
    ReglaRepositorio,
    VariableRepositorio,
)
from apps.validacion.engine import MotorValidacion
from apps.validacion.entities import IncidenciaValidacion, ResultadoValidacion
from apps.validacion.repositories import (
    DjangoValidacionBaseRepositorio,
    ValidacionBaseRepositorio,
)


class ValidarBaseConocimiento:
    """Caso de uso para ejecutar el diagnóstico completo de la base de conocimiento (HU-18)."""

    def __init__(
        self,
        repo_val: Optional[ValidacionBaseRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
        repo_hecho: Optional[HechoRepositorio] = None,
        repo_var: Optional[VariableRepositorio] = None,
        repo_regla: Optional[ReglaRepositorio] = None,
    ):
        self.repo_val = repo_val or DjangoValidacionBaseRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()
        self.repo_var = repo_var or DjangoVariableRepositorio()
        self.repo_regla = repo_regla or DjangoReglaRepositorio()

    @transaction.atomic
    def ejecutar(self, base_conocimiento_id: UUID) -> ResultadoValidacion:
        bc = self.repo_bc.obtener_por_id(base_conocimiento_id)
        if not bc:
            raise BaseConocimientoNoEncontrada(base_conocimiento_id)

        hechos = self.repo_hecho.listar_por_base(base_conocimiento_id)
        variables = self.repo_var.listar_por_base(base_conocimiento_id)
        reglas = self.repo_regla.listar_por_base(base_conocimiento_id)

        # Ejecutar motor de validación desacoplado
        resultado = MotorValidacion.validar(
            base_conocimiento_id=base_conocimiento_id,
            hechos=hechos,
            variables=variables,
            reglas=reglas,
        )

        # Persistir resultado e incidencias
        return self.repo_val.guardar(resultado)


class ConsultarValidacion:
    """Caso de uso para consultar una validación por su ID."""

    def __init__(self, repo_val: Optional[ValidacionBaseRepositorio] = None):
        self.repo_val = repo_val or DjangoValidacionBaseRepositorio()

    def ejecutar(self, id_validacion: UUID) -> Optional[ResultadoValidacion]:
        return self.repo_val.obtener_por_id(id_validacion)


class ConsultarUltimaValidacion:
    """Caso de uso para consultar el último reporte de validación de una base."""

    def __init__(self, repo_val: Optional[ValidacionBaseRepositorio] = None):
        self.repo_val = repo_val or DjangoValidacionBaseRepositorio()

    def ejecutar(self, base_conocimiento_id: UUID) -> Optional[ResultadoValidacion]:
        return self.repo_val.obtener_ultima_por_base(base_conocimiento_id)


class ConsultarIncidenciasValidacion:
    """Caso de uso para consultar reporte detallado de incidencias y sugerencias (HU-19)."""

    def __init__(self, repo_val: Optional[ValidacionBaseRepositorio] = None):
        self.repo_val = repo_val or DjangoValidacionBaseRepositorio()

    def ejecutar(
        self,
        id_validacion: UUID,
        severidad: Optional[str] = None,
        tipo: Optional[str] = None,
    ) -> List[IncidenciaValidacion]:
        return self.repo_val.listar_incidencias(
            id_validacion=id_validacion, severidad=severidad, tipo=tipo
        )
