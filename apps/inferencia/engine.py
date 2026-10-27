"""
Motor de Inferencia por Encadenamiento hacia Adelante (Forward Chaining).
Completamente desacoplado del framework web (sin Django ni DRF).
Soporta ejecución completa y ejecución paso a paso (Sprint 1 + Sprint 2).
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
from apps.inferencia.trace import (
    EntradaTraza,
    PasoEjecucionResultado,
    ResultadoInferencia,
)
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
        if valor is None or (isinstance(valor, str) and not valor.strip()):
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

    @staticmethod
    def construir_mapa_ids(
        hechos_iniciales: List[Hecho],
        reglas: List[Regla],
        variables: Optional[List[Variable]] = None,
    ) -> Dict[str, str]:
        """Construye un mapa de UUID -> Nombre para resolución de condiciones y conclusiones."""
        variables = variables or []
        mapa: Dict[str, str] = {}
        for h in hechos_iniciales:
            mapa[str(h.id)] = h.nombre
        for v in variables:
            mapa[str(v.id)] = v.nombre
        for r in reglas:
            for conc in r.conclusiones:
                if conc.hecho_resultante_id:
                    for h in hechos_iniciales:
                        if h.id == conc.hecho_resultante_id:
                            mapa[str(conc.hecho_resultante_id)] = h.nombre
                if conc.variable_resultante_id:
                    for v in variables:
                        if v.id == conc.variable_resultante_id:
                            mapa[str(conc.variable_resultante_id)] = v.nombre
        return mapa

    def ejecutar_un_paso(
        self,
        memoria_trabajo: Dict[str, Any],
        reglas_ejecutadas: Set[UUID],
        reglas: List[Regla],
        variables: Optional[List[Variable]] = None,
        mapa_ids_a_nombres: Optional[Dict[str, str]] = None,
        numero_paso: int = 1,
    ) -> PasoEjecucionResultado:
        """
        Ejecuta exactamente un ciclo de inferencia:
        1. Cotejo: evalúa reglas activas pendientes contra la memoria de trabajo actual.
        2. Construcción del conjunto de conflicto.
        3. Selección de regla ganadora mediante resolución determinista de conflictos.
        4. Disparo de conclusiones y actualización de memoria de trabajo.
        """
        variables = variables or []
        mapa_ids_a_nombres = mapa_ids_a_nombres or {}
        for v in variables:
            mapa_ids_a_nombres[str(v.id)] = v.nombre

        memoria_pre = dict(memoria_trabajo)
        reglas_activas = [r for r in reglas if r.activa and r.id not in reglas_ejecutadas]
        conjunto_conflicto: List[Regla] = []
        trazas: List[EntradaTraza] = []
        orden_traza = 1
        condiciones_por_regla: Dict[UUID, List[Dict[str, Any]]] = {}

        for regla in reglas_activas:
            if not regla.condiciones:
                continue

            todas_cumplen = True
            condiciones_evaluadas = []
            for condicion in regla.condiciones:
                cumple = EvaluadorCondicion.evaluar(
                    condicion=condicion,
                    memoria_trabajo=memoria_trabajo,
                    mapa_ids_a_nombres=mapa_ids_a_nombres,
                )
                if not cumple:
                    todas_cumplen = False
                condiciones_evaluadas.append({"condicion_id": str(condicion.id), "resultado": bool(cumple)})
            condiciones_por_regla[regla.id] = condiciones_evaluadas

            trazas.append(
                EntradaTraza(
                    regla_id=regla.id,
                    regla_nombre=regla.nombre,
                    orden=orden_traza,
                    estado=EstadoReglaInferencia.EVALUADA,
                    paso_numero=numero_paso,
                    condiciones_cumplidas=todas_cumplen,
                    condiciones_evaluadas=condiciones_evaluadas,
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
                        paso_numero=numero_paso,
                        condiciones_cumplidas=True,
                        condiciones_evaluadas=condiciones_evaluadas,
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
                        paso_numero=numero_paso,
                        condiciones_cumplidas=False,
                        condiciones_evaluadas=condiciones_evaluadas,
                    )
                )
                orden_traza += 1

        if not conjunto_conflicto:
            return PasoEjecucionResultado(
                numero_paso=numero_paso,
                finalizado=True,
                memoria_trabajo_pre=memoria_pre,
                memoria_trabajo_post=dict(memoria_trabajo),
                trazas_paso=trazas,
                descripcion="Inferencia detenida: no existen más reglas cuyas condiciones se cumplan en la memoria de trabajo.",
            )

        # Resolver conflicto con detalle determinista
        resultado_conflicto = self.estrategia_resolucion.resolver_con_detalle(conjunto_conflicto)
        regla_ganadora = resultado_conflicto.regla_ganadora

        # Disparar conclusiones
        memoria_post = dict(memoria_trabajo)
        hechos_generados: List[Dict[str, Any]] = []
        resultados_paso = []

        for conc in regla_ganadora.conclusiones:
            nombre_destino = None
            if conc.hecho_resultante_id:
                nombre_destino = mapa_ids_a_nombres.get(str(conc.hecho_resultante_id))
            elif conc.variable_resultante_id:
                nombre_destino = mapa_ids_a_nombres.get(str(conc.variable_resultante_id))

            if not nombre_destino:
                nombre_destino = str(
                    conc.hecho_resultante_id or conc.variable_resultante_id or "resultado"
                )

            valor_consecuente = conc.valor_resultante
            memoria_post[nombre_destino] = valor_consecuente
            hechos_generados.append(
                {
                    "nombre": nombre_destino,
                    "valor": valor_consecuente,
                    "regla_id": str(regla_ganadora.id),
                    "regla_nombre": regla_ganadora.nombre,
                    "procedencia": "DERIVADO",
                }
            )
            resultados_paso.append(f"{nombre_destino} = {valor_consecuente}")

        res_str = ", ".join(resultados_paso) if resultados_paso else "Regla ejecutada sin cambios."
        trazas.append(
            EntradaTraza(
                regla_id=regla_ganadora.id,
                regla_nombre=regla_ganadora.nombre,
                orden=orden_traza,
                estado=EstadoReglaInferencia.EJECUTADA,
                paso_numero=numero_paso,
                condiciones_cumplidas=True,
                condiciones_evaluadas=condiciones_por_regla[regla_ganadora.id],
                resultado_generado=res_str,
            )
        )

        descripcion = (
            f"Paso {numero_paso}: Regla '{regla_ganadora.nombre}' seleccionada entre "
            f"{len(conjunto_conflicto)} regla(s) candidata(s) y disparada. Conclusión: {res_str}"
        )

        conclusion_final = str(hechos_generados[-1]["valor"]) if hechos_generados else None

        return PasoEjecucionResultado(
            numero_paso=numero_paso,
            finalizado=False,
            memoria_trabajo_pre=memoria_pre,
            memoria_trabajo_post=memoria_post,
            regla_disparada=regla_ganadora,
            candidatas_conflicto=conjunto_conflicto,
            hechos_generados=hechos_generados,
            trazas_paso=trazas,
            criterio_conflicto=resultado_conflicto.criterio_aplicado,
            explicacion_conflicto=resultado_conflicto.explicacion_resolucion,
            motivos_descarte_conflicto=resultado_conflicto.motivos_descarte,
            conclusion_final=conclusion_final,
            descripcion=descripcion,
        )

    def ejecutar_un_paso_regla(
        self,
        memoria_trabajo: Dict[str, Any],
        regla: Regla,
        numero_paso: int = 1,
        variables: Optional[List[Variable]] = None,
        mapa_ids_a_nombres: Optional[Dict[str, str]] = None,
        es_ultimo_paso: bool = False,
    ) -> PasoEjecucionResultado:
        """
        Evalúa y ejecuta exactamente una regla discreta en el ciclo de simulación paso a paso.
        Permite al usuario observar individualmente cómo se evaluó esa regla y qué devolvió.
        """
        variables = variables or []
        mapa_ids_a_nombres = mapa_ids_a_nombres or {}
        for v in variables:
            mapa_ids_a_nombres[str(v.id)] = v.nombre

        memoria_pre = dict(memoria_trabajo)
        trazas: List[EntradaTraza] = []
        orden_traza = 1

        condiciones_evaluadas = []
        todas_cumplen = bool(regla.condiciones)
        for condicion in (regla.condiciones or []):
            cumple = EvaluadorCondicion.evaluar(
                condicion=condicion,
                memoria_trabajo=memoria_trabajo,
                mapa_ids_a_nombres=mapa_ids_a_nombres,
            )
            condiciones_evaluadas.append({"condicion_id": str(condicion.id), "resultado": bool(cumple)})
            if not cumple:
                todas_cumplen = False

        trazas.append(
            EntradaTraza(
                regla_id=regla.id,
                regla_nombre=regla.nombre,
                orden=orden_traza,
                estado=EstadoReglaInferencia.EVALUADA,
                paso_numero=numero_paso,
                condiciones_cumplidas=todas_cumplen,
                condiciones_evaluadas=condiciones_evaluadas,
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
                    paso_numero=numero_paso,
                    condiciones_cumplidas=True,
                    condiciones_evaluadas=condiciones_evaluadas,
                )
            )
            orden_traza += 1

            # Disparar conclusiones
            memoria_post = dict(memoria_trabajo)
            hechos_generados: List[Dict[str, Any]] = []
            resultados_paso = []

            for conc in regla.conclusiones:
                nombre_destino = None
                if conc.hecho_resultante_id:
                    nombre_destino = mapa_ids_a_nombres.get(str(conc.hecho_resultante_id))
                elif conc.variable_resultante_id:
                    nombre_destino = mapa_ids_a_nombres.get(str(conc.variable_resultante_id))

                if not nombre_destino:
                    nombre_destino = str(
                        conc.hecho_resultante_id or conc.variable_resultante_id or "resultado"
                    )

                valor_consecuente = conc.valor_resultante
                memoria_post[nombre_destino] = valor_consecuente
                hechos_generados.append(
                    {
                        "nombre": nombre_destino,
                        "valor": valor_consecuente,
                        "regla_id": str(regla.id),
                        "regla_nombre": regla.nombre,
                        "procedencia": "DERIVADO",
                    }
                )
                resultados_paso.append(f"{nombre_destino} = {valor_consecuente}")

            res_str = ", ".join(resultados_paso) if resultados_paso else "Regla ejecutada sin cambios."
            trazas.append(
                EntradaTraza(
                    regla_id=regla.id,
                    regla_nombre=regla.nombre,
                    orden=orden_traza,
                    estado=EstadoReglaInferencia.EJECUTADA,
                    paso_numero=numero_paso,
                    condiciones_cumplidas=True,
                    condiciones_evaluadas=condiciones_evaluadas,
                    resultado_generado=res_str,
                )
            )

            descripcion = (
                f"Paso {numero_paso}: Regla '{regla.nombre}' evaluada y activada. Devolvió: {res_str}"
            )
            conclusion_final = str(hechos_generados[-1]["valor"]) if hechos_generados else None

            return PasoEjecucionResultado(
                numero_paso=numero_paso,
                finalizado=es_ultimo_paso,
                memoria_trabajo_pre=memoria_pre,
                memoria_trabajo_post=memoria_post,
                regla_disparada=regla,
                candidatas_conflicto=[regla],
                hechos_generados=hechos_generados,
                trazas_paso=trazas,
                criterio_conflicto="EVALUACION_INDIVIDUAL_POR_REGLA",
                explicacion_conflicto=f"Evaluación directa individual de la regla '{regla.nombre}'.",
                motivos_descarte_conflicto={},
                conclusion_final=conclusion_final,
                descripcion=descripcion,
            )
        else:
            trazas.append(
                EntradaTraza(
                    regla_id=regla.id,
                    regla_nombre=regla.nombre,
                    orden=orden_traza,
                    estado=EstadoReglaInferencia.RECHAZADA,
                    paso_numero=numero_paso,
                    condiciones_cumplidas=False,
                    condiciones_evaluadas=condiciones_evaluadas,
                    resultado_generado="Condiciones no satisfechas.",
                )
            )
            descripcion = (
                f"Paso {numero_paso}: Regla '{regla.nombre}' evaluada. Condiciones no satisfechas."
            )
            return PasoEjecucionResultado(
                numero_paso=numero_paso,
                finalizado=es_ultimo_paso,
                memoria_trabajo_pre=memoria_pre,
                memoria_trabajo_post=memoria_pre,
                regla_disparada=None,
                candidatas_conflicto=[],
                hechos_generados=[],
                trazas_paso=trazas,
                criterio_conflicto="EVALUACION_INDIVIDUAL_POR_REGLA",
                explicacion_conflicto=f"La regla '{regla.nombre}' no cumplió todas sus premisas.",
                motivos_descarte_conflicto={},
                conclusion_final=None,
                descripcion=descripcion,
            )

    def ejecutar(
        self,
        hechos_iniciales: List[Hecho],
        reglas: List[Regla],
        variables: Optional[List[Variable]] = None,
    ) -> ResultadoInferencia:
        """
        Ejecuta el ciclo completo de encadenamiento hacia adelante, registrando pasos y conflictos.
        """
        variables = variables or []
        mapa_ids_a_nombres = self.construir_mapa_ids(hechos_iniciales, reglas, variables)

        # 1. Cargar memoria de trabajo con hechos iniciales
        memoria_trabajo: Dict[str, Any] = {}
        hechos_iniciales_reporte: List[Dict[str, Any]] = []

        for h in hechos_iniciales:
            tipo_str = h.tipo_dato.value if hasattr(h.tipo_dato, "value") else h.tipo_dato
            val_parseado = self._parsear_valor_hecho(h.valor, tipo_str)
            if val_parseado is not None:
                memoria_trabajo[h.nombre] = val_parseado
            hechos_iniciales_reporte.append(
                {
                    "nombre": h.nombre,
                    "valor": val_parseado,
                }
            )

        logger.debug(f"Memoria de trabajo inicial: {memoria_trabajo}")

        reglas_ejecutadas: Set[UUID] = set()
        trazas_acumuladas: List[EntradaTraza] = []
        hechos_generados_totales: List[Dict[str, Any]] = []
        pasos_ejecutados: List[PasoEjecucionResultado] = []
        historial_estados: Set[str] = set()

        iteracion = 0
        orden_traza_global = 1
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

            resultado_paso = self.ejecutar_un_paso(
                memoria_trabajo=memoria_trabajo,
                reglas_ejecutadas=reglas_ejecutadas,
                reglas=reglas,
                variables=variables,
                mapa_ids_a_nombres=mapa_ids_a_nombres,
                numero_paso=iteracion,
            )

            # Re-secuenciar orden de trazas globalmente
            for t in resultado_paso.trazas_paso:
                t.orden = orden_traza_global
                orden_traza_global += 1
                trazas_acumuladas.append(t)

            pasos_ejecutados.append(resultado_paso)

            if resultado_paso.finalizado:
                break

            # Actualizar memoria y estado
            memoria_trabajo = resultado_paso.memoria_trabajo_post
            if resultado_paso.regla_disparada:
                reglas_ejecutadas.add(resultado_paso.regla_disparada.id)

            for hg in resultado_paso.hechos_generados:
                hechos_generados_totales.append(hg)
                conclusion_final = str(hg["valor"])

        if not conclusion_final and hechos_generados_totales:
            conclusion_final = str(hechos_generados_totales[-1]["valor"])

        return ResultadoInferencia(
            estado=EstadoEjecucion.FINALIZADA,
            hechos_iniciales=hechos_iniciales_reporte,
            hechos_generados=hechos_generados_totales,
            reglas_evaluadas=trazas_acumuladas,
            conclusion_final=conclusion_final,
            total_iteraciones=iteracion,
            pasos=pasos_ejecutados,
        )
