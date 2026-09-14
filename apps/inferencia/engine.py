"""
Motor de Inferencia por Encadenamiento hacia Adelante (Forward Chaining).
Completamente desacoplado del framework web (sin Django ni DRF).
"""
import json
import logging
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from apps.base_conocimiento.entities import Hecho, Regla, Variable
from apps.inferencia.conflict_resolution import (
    EstrategiaResolucionConflictos,
    ResolucionPorPrioridad,
)
from apps.inferencia.evaluator import EvaluadorCondicion
from apps.inferencia.exceptions import LimiteIteracionesAlcanzado
from apps.inferencia.trace import EntradaTraza, ResultadoInferencia
from compartido.constantes.enums import EstadoEjecucion, EstadoReglaInferencia

logger = logging.getLogger("motor_inferencia")


class MotorInferencia:
    """
    Motor de Inferencia por encadenamiento hacia adelante.
    Aplica ciclo: Cotejo -> Resolución de Conflictos -> Ejecución.
    """

    def __init__(
        self,
        estrategia_resolucion: Optional[EstrategiaResolucionConflictos] = None,
        max_iteraciones: int = 100,
    ):
        self.estrategia_resolucion = estrategia_resolucion or ResolucionPorPrioridad()
        self.max_iteraciones = max_iteraciones

    @staticmethod
    def _parsear_valor_hecho(valor: Any, tipo_dato: str) -> Any:
        if valor is None:
            return None
        tipo = str(tipo_dato).upper()
        if tipo == "BOOLEANO":
            return EvaluadorCondicion._normalizar_booleano(valor)
        if tipo == "ENTERO":
            try:
                return int(valor)
            except (ValueError, TypeError):
                return str(valor)
        if tipo == "DECIMAL":
            try:
                return float(valor)
            except (ValueError, TypeError):
                return str(valor)
        return str(valor)

    def ejecutar(
        self,
        hechos_iniciales: List[Hecho],
        reglas: List[Regla],
        variables: Optional[List[Variable]] = None,
    ) -> ResultadoInferencia:
        """
        Ejecuta el ciclo completo de encadenamiento hacia adelante.
        """
        variables = variables or []
        mapa_ids_a_nombres: Dict[str, str] = {}

        for h in hechos_iniciales:
            mapa_ids_a_nombres[str(h.id)] = h.nombre

        for v in variables:
            mapa_ids_a_nombres[str(v.id)] = v.nombre

        # Mapear destinos de conclusiones que apunten a hechos o variables
        for r in reglas:
            for conc in r.conclusiones:
                if conc.hecho_resultante_id:
                    for h in hechos_iniciales:
                        if h.id == conc.hecho_resultante_id:
                            mapa_ids_a_nombres[str(conc.hecho_resultante_id)] = h.nombre
                if conc.variable_resultante_id:
                    for v in variables:
                        if v.id == conc.variable_resultante_id:
                            mapa_ids_a_nombres[str(conc.variable_resultante_id)] = v.nombre

        # 1. Cargar memoria de trabajo con hechos iniciales
        memoria_trabajo: Dict[str, Any] = {}
        hechos_iniciales_reporte: List[Dict[str, Any]] = []

        for h in hechos_iniciales:
            tipo_str = h.tipo_dato.value if hasattr(h.tipo_dato, "value") else h.tipo_dato
            val_parseado = self._parsear_valor_hecho(h.valor, tipo_str)
            memoria_trabajo[h.nombre] = val_parseado
            hechos_iniciales_reporte.append(
                {
                    "nombre": h.nombre,
                    "valor": val_parseado,
                }
            )

        logger.debug(f"Memoria de trabajo inicial: {memoria_trabajo}")

        # Solo reglas activas
        reglas_activas = [r for r in reglas if r.activa]
        reglas_ejecutadas: Set[UUID] = set()
        trazas: List[EntradaTraza] = []
        hechos_generados: List[Dict[str, Any]] = []
        historial_estados: Set[str] = set()

        iteracion = 0
        orden_traza = 1
        conclusion_final = None

        while True:
            iteracion += 1
            if iteracion > self.max_iteraciones:
                logger.error(f"Límite de iteraciones alcanzado: {self.max_iteraciones}")
                raise LimiteIteracionesAlcanzado(self.max_iteraciones)

            # Detección de repetición de estado para evitar bucles infinitos
            snapshot_estado = json.dumps(memoria_trabajo, sort_keys=True, default=str)
            if snapshot_estado in historial_estados:
                logger.info("Ciclo de estado repetido detectado. Deteniendo inferencia.")
                break
            historial_estados.add(snapshot_estado)

            conjunto_conflicto: List[Regla] = []

            # Evaluar reglas activas que aún no hayan sido ejecutadas
            for regla in reglas_activas:
                if regla.id in reglas_ejecutadas:
                    continue

                if not regla.condiciones:
                    continue

                todas_cumplen = True
                for condicion in regla.condiciones:
                    cumple = EvaluadorCondicion.evaluar(
                        condicion=condicion,
                        memoria_trabajo=memoria_trabajo,
                        mapa_ids_a_nombres=mapa_ids_a_nombres,
                    )
                    if not cumple:
                        todas_cumplen = False
                        break

                trazas.append(
                    EntradaTraza(
                        regla_id=regla.id,
                        regla_nombre=regla.nombre,
                        orden=orden_traza,
                        estado=EstadoReglaInferencia.EVALUADA,
                        condiciones_cumplidas=todas_cumplen,
                    )
                )
                orden_traza += 1

                if todas_cumplen:
                    trazas.append(
                        EntradaTraza(
                            regla_id=regla.id,
                            regla_nombre=regla.nombre,
                            orden=orden_traza,
                            estado=EstadoReglaInferencia.ACTIVADA,
                            condiciones_cumplidas=True,
                        )
                    )
                    orden_traza += 1
                    conjunto_conflicto.append(regla)
                else:
                    trazas.append(
                        EntradaTraza(
                            regla_id=regla.id,
                            regla_nombre=regla.nombre,
                            orden=orden_traza,
                            estado=EstadoReglaInferencia.RECHAZADA,
                            condiciones_cumplidas=False,
                        )
                    )
                    orden_traza += 1

            if not conjunto_conflicto:
                logger.debug(
                    "Conjunto de conflicto vacío. Proceso de inferencia finalizado."
                )
                break

            # Resolver conflicto con la estrategia establecida
            regla_ganadora = self.estrategia_resolucion.resolver(conjunto_conflicto)
            logger.debug(
                f"Regla seleccionada para disparar: {regla_ganadora.nombre} (P: {regla_ganadora.prioridad})"
            )

            # Ejecutar conclusiones de la regla ganadora
            resultados_paso = []
            for conc in regla_ganadora.conclusiones:
                nombre_destino = None
                if conc.hecho_resultante_id:
                    nombre_destino = mapa_ids_a_nombres.get(str(conc.hecho_resultante_id))
                elif conc.variable_resultante_id:
                    nombre_destino = mapa_ids_a_nombres.get(
                        str(conc.variable_resultante_id)
                    )

                if not nombre_destino:
                    nombre_destino = str(
                        conc.hecho_resultante_id
                        or conc.variable_resultante_id
                        or "resultado"
                    )

                valor_consecuente = conc.valor_resultante
                memoria_trabajo[nombre_destino] = valor_consecuente
                hechos_generados.append(
                    {
                        "nombre": nombre_destino,
                        "valor": valor_consecuente,
                    }
                )
                resultados_paso.append(f"{nombre_destino} = {valor_consecuente}")
                conclusion_final = valor_consecuente

            if resultados_paso:
                resultado_str = ", ".join(resultados_paso)
            else:
                resultado_str = "Regla ejecutada sin modificaciones directas."

            trazas.append(
                EntradaTraza(
                    regla_id=regla_ganadora.id,
                    regla_nombre=regla_ganadora.nombre,
                    orden=orden_traza,
                    estado=EstadoReglaInferencia.EJECUTADA,
                    condiciones_cumplidas=True,
                    resultado_generado=resultado_str,
                )
            )
            orden_traza += 1
            reglas_ejecutadas.add(regla_ganadora.id)

        if not conclusion_final and hechos_generados:
            conclusion_final = str(hechos_generados[-1]["valor"])

        return ResultadoInferencia(
            estado=EstadoEjecucion.FINALIZADA,
            hechos_iniciales=hechos_iniciales_reporte,
            hechos_generados=hechos_generados,
            reglas_evaluadas=trazas,
            conclusion_final=conclusion_final,
            total_iteraciones=iteracion,
        )
