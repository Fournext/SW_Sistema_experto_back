"""
Servicios y casos de uso para el módulo de Inferencia.
"""
from typing import List, Optional
from uuid import UUID
from django.conf import settings
from django.utils import timezone

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
from apps.inferencia.engine import MotorInferencia
from apps.inferencia.entities import DetalleInferencia, EjecucionInferencia
from apps.inferencia.exceptions import EjecucionInferenciaNoEncontrada
from apps.inferencia.repositories import (
    DetalleInferenciaRepositorio,
    DjangoDetalleInferenciaRepositorio,
    DjangoEjecucionInferenciaRepositorio,
    EjecucionInferenciaRepositorio,
)
from apps.inferencia.trace import ResultadoInferencia
from apps.sistemas_expertos.exceptions import SistemaExpertoNoEncontrado
from apps.sistemas_expertos.repositories import (
    DjangoSistemaExpertoRepositorio,
    SistemaExpertoRepositorio,
)
from compartido.constantes.enums import EstadoEjecucion


class EjecutarInferencia:
    """Orquesta la ejecución de inferencia para un sistema experto."""

    def __init__(
        self,
        repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None,
        repo_detalle: Optional[DetalleInferenciaRepositorio] = None,
        repo_se: Optional[SistemaExpertoRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
        repo_hecho: Optional[HechoRepositorio] = None,
        repo_var: Optional[VariableRepositorio] = None,
        repo_regla: Optional[ReglaRepositorio] = None,
    ):
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()
        self.repo_detalle = repo_detalle or DjangoDetalleInferenciaRepositorio()
        self.repo_se = repo_se or DjangoSistemaExpertoRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()
        self.repo_var = repo_var or DjangoVariableRepositorio()
        self.repo_regla = repo_regla or DjangoReglaRepositorio()

    def ejecutar(self, sistema_experto_id: UUID) -> ResultadoInferencia:
        # 1. Validar existencia del sistema experto
        se = self.repo_se.obtener_por_id(sistema_experto_id)
        if not se:
            raise SistemaExpertoNoEncontrado(sistema_experto_id)

        # 2. Cargar base de conocimiento
        bc = self.repo_bc.obtener_por_sistema_experto_id(sistema_experto_id)
        if not bc:
            raise SistemaExpertoNoEncontrado(
                f"El sistema experto {sistema_experto_id} no tiene base de conocimiento."
            )

        # 3. Cargar hechos, variables y reglas activas
        hechos = self.repo_hecho.listar_por_base(bc.id)
        variables = self.repo_var.listar_por_base(bc.id)
        reglas_activas = self.repo_regla.listar_activas_por_base(bc.id)

        # 4. Registrar ejecución en estado INICIADA -> EJECUTANDO
        ejecucion = EjecucionInferencia(
            sistema_experto_id=sistema_experto_id,
            estado=EstadoEjecucion.EJECUTANDO,
        )
        ejecucion = self.repo_ejecucion.guardar(ejecucion)

        # 5. Instanciar y ejecutar el motor desacoplado
        max_iter = getattr(settings, "MAX_INFERENCE_ITERATIONS", 100)
        motor = MotorInferencia(max_iteraciones=max_iter)

        try:
            resultado = motor.ejecutar(
                hechos_iniciales=hechos,
                reglas=reglas_activas,
                variables=variables,
            )
            resultado.ejecucion_id = ejecucion.id

            # 6. Persistir traza de detalles
            detalles_entidades = [
                DetalleInferencia(
                    ejecucion_id=ejecucion.id,
                    regla_id=t.regla_id,
                    orden=t.orden,
                    estado_regla=t.estado,
                    condiciones_cumplidas=t.condiciones_cumplidas,
                    resultado_generado=t.resultado_generado,
                )
                for t in resultado.reglas_evaluadas
            ]
            if detalles_entidades:
                self.repo_detalle.guardar_lote(detalles_entidades)

            # 7. Actualizar ejecución como FINALIZADA
            ejecucion.estado = EstadoEjecucion.FINALIZADA
            ejecucion.fecha_fin = timezone.now()
            ejecucion.conclusion_final = resultado.conclusion_final
            self.repo_ejecucion.guardar(ejecucion)

            return resultado

        except Exception as e:
            ejecucion.estado = EstadoEjecucion.ERROR
            ejecucion.fecha_fin = timezone.now()
            ejecucion.conclusion_final = f"Error: {str(e)}"
            self.repo_ejecucion.guardar(ejecucion)
            raise


class ConsultarEjecucion:
    def __init__(self, repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None):
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()

    def ejecutar(self, id_ejecucion: UUID) -> EjecucionInferencia:
        ejecucion = self.repo_ejecucion.obtener_por_id(id_ejecucion)
        if not ejecucion:
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)
        return ejecucion


class ConsultarTrazaInferencia:
    def __init__(
        self,
        repo_detalle: Optional[DetalleInferenciaRepositorio] = None,
        repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None,
    ):
        self.repo_detalle = repo_detalle or DjangoDetalleInferenciaRepositorio()
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()

    def ejecutar(self, id_ejecucion: UUID) -> List[DetalleInferencia]:
        if not self.repo_ejecucion.obtener_por_id(id_ejecucion):
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)
        return self.repo_detalle.listar_por_ejecucion(id_ejecucion)
