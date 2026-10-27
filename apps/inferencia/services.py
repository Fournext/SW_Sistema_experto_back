"""
Servicios y casos de uso para el módulo de Inferencia y Simulación (Sprint 1 + Sprint 2).
"""
import copy
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.base_conocimiento.entities import Hecho
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
from apps.inferencia.entities import (
    ConflictoInferencia,
    ConflictoReglaCandidata,
    DetalleInferencia,
    EjecucionInferencia,
    ExplicacionConclusion,
    HechoInferido,
    PasoInferencia,
)
from apps.inferencia.exceptions import EjecucionInferenciaNoEncontrada, LimiteIteracionesAlcanzado
from apps.inferencia.recorrido import nuevo_recorrido, ordenar_reglas, pendientes_recorrido, cerrar_vuelta, asignar_paso_visual
from apps.inferencia.explicabilidad import MotorExplicabilidad
from apps.inferencia.repositories import (
    ConflictoInferenciaRepositorio,
    DetalleInferenciaRepositorio,
    DjangoConflictoInferenciaRepositorio,
    DjangoDetalleInferenciaRepositorio,
    DjangoEjecucionInferenciaRepositorio,
    DjangoExplicacionConclusionRepositorio,
    DjangoHechoInferidoRepositorio,
    DjangoPasoInferenciaRepositorio,
    EjecucionInferenciaRepositorio,
    ExplicacionConclusionRepositorio,
    HechoInferidoRepositorio,
    PasoInferenciaRepositorio,
)
from apps.inferencia.trace import ResultadoInferencia, PasoEjecucionResultado
from apps.sistemas_expertos.exceptions import SistemaExpertoNoEncontrado
from apps.sistemas_expertos.repositories import (
    DjangoSistemaExpertoRepositorio,
    SistemaExpertoRepositorio,
)
from compartido.constantes.enums import (
    EstadoEjecucion,
    ModoInferencia,
    ProcedenciaHecho,
    TipoDato,
)


class EjecutarInferencia:
    """Orquesta la ejecución automática completa de inferencia para un sistema experto."""

    def __init__(
        self,
        repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None,
        repo_detalle: Optional[DetalleInferenciaRepositorio] = None,
        repo_paso: Optional[PasoInferenciaRepositorio] = None,
        repo_hecho_inf: Optional[HechoInferidoRepositorio] = None,
        repo_conflicto: Optional[ConflictoInferenciaRepositorio] = None,
        repo_explicacion: Optional[ExplicacionConclusionRepositorio] = None,
        repo_se: Optional[SistemaExpertoRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
        repo_hecho: Optional[HechoRepositorio] = None,
        repo_var: Optional[VariableRepositorio] = None,
        repo_regla: Optional[ReglaRepositorio] = None,
    ):
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()
        self.repo_detalle = repo_detalle or DjangoDetalleInferenciaRepositorio()
        self.repo_paso = repo_paso or DjangoPasoInferenciaRepositorio()
        self.repo_hecho_inf = repo_hecho_inf or DjangoHechoInferidoRepositorio()
        self.repo_conflicto = repo_conflicto or DjangoConflictoInferenciaRepositorio()
        self.repo_explicacion = repo_explicacion or DjangoExplicacionConclusionRepositorio()
        self.repo_se = repo_se or DjangoSistemaExpertoRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()
        self.repo_var = repo_var or DjangoVariableRepositorio()
        self.repo_regla = repo_regla or DjangoReglaRepositorio()

    @transaction.atomic
    def ejecutar(
        self,
        sistema_experto_id: UUID,
        hechos_personalizados: Optional[List[Dict[str, Any]]] = None,
    ) -> ResultadoInferencia:
        se = self.repo_se.obtener_por_id(sistema_experto_id)
        if not se:
            raise SistemaExpertoNoEncontrado(sistema_experto_id)

        bc = self.repo_bc.obtener_por_sistema_experto_id(sistema_experto_id)
        if not bc:
            raise SistemaExpertoNoEncontrado(
                f"El sistema experto {sistema_experto_id} no tiene base de conocimiento."
            )

        hechos_db = self.repo_hecho.listar_por_base(bc.id)
        variables = self.repo_var.listar_por_base(bc.id)
        reglas_activas = self.repo_regla.listar_activas_por_base(bc.id)

        # Si se introdujeron hechos en simulación interactiva, usarlos sin mutar la BD
        hechos_a_usar = hechos_db
        if hechos_personalizados is not None:
            # Las condiciones y conclusiones referencian los UUID originales.
            # Sobrescribir copias mantiene esas referencias y los valores base no respondidos.
            hechos_a_usar = copy.deepcopy(hechos_db)
            hechos_por_nombre = {h.nombre.strip().casefold(): h for h in hechos_a_usar}
            variables_por_nombre = {v.nombre.strip().casefold(): v for v in variables}
            for hp in hechos_personalizados:
                nombre = str(hp.get("nombre") or "").strip()
                clave = nombre.casefold()
                hecho = hechos_por_nombre.get(clave)
                if hecho is None:
                    variable = variables_por_nombre.get(clave)
                    hecho = Hecho(
                        id=variable.id if variable else uuid4(),
                        base_conocimiento_id=bc.id,
                        nombre=variable.nombre if variable else nombre,
                        tipo_dato=variable.tipo_dato if variable else TipoDato.TEXTO,
                    )
                    hechos_a_usar.append(hecho)
                    hechos_por_nombre[clave] = hecho
                hecho.valor = hp.get("valor")
                if hp.get("tipo_dato"):
                    hecho.tipo_dato = hp["tipo_dato"]
                if "opciones" in hp:
                    hecho.opciones = hp["opciones"]

        hechos_snapshot = [
            {
                "nombre": h.nombre,
                "valor": h.valor,
                "tipo_dato": str(h.tipo_dato),
                "opciones": getattr(h, "opciones", []),
            }
            for h in hechos_a_usar
        ]

        # Registrar ejecución
        ejecucion = EjecucionInferencia(
            sistema_experto_id=sistema_experto_id,
            estado=EstadoEjecucion.EJECUTANDO,
            modo=ModoInferencia.AUTOMATICA,
            hechos_iniciales_snapshot=hechos_snapshot,
            es_simulacion=False,
        )
        ejecucion = self.repo_ejecucion.guardar(ejecucion)

        max_iter = getattr(settings, "MAX_INFERENCE_ITERATIONS", 100)
        motor = MotorInferencia(max_iteraciones=max_iter)

        try:
            resultado = motor.ejecutar(
                hechos_iniciales=hechos_a_usar,
                reglas=reglas_activas,
                variables=variables,
            )
            resultado.ejecucion_id = ejecucion.id

            # 1. Guardar detalles de traza (Sprint 1)
            detalles_entidades = [
                DetalleInferencia(
                    ejecucion_id=ejecucion.id,
                    regla_id=t.regla_id,
                    orden=t.orden,
                    estado_regla=t.estado,
                    condiciones_cumplidas=t.condiciones_cumplidas,
                    condiciones_evaluadas=t.condiciones_evaluadas,
                    paso_numero=t.paso_numero,
                    paso_visual=t.paso_visual,
                    resultado_generado=t.resultado_generado,
                )
                for t in resultado.reglas_evaluadas
            ]
            if detalles_entidades:
                self.repo_detalle.guardar_lote(detalles_entidades)

            # 2. Persistir pasos estructurados, hechos derivados y conflictos (Sprint 2)
            for paso_res in resultado.pasos:
                regla_id = paso_res.regla_disparada.id if paso_res.regla_disparada else None
                paso_entidad = PasoInferencia(
                    ejecucion_id=ejecucion.id,
                    numero_paso=paso_res.numero_paso,
                    regla_disparada_id=regla_id,
                    memoria_trabajo_pre=paso_res.memoria_trabajo_pre,
                    memoria_trabajo_post=paso_res.memoria_trabajo_post,
                    descripcion=paso_res.descripcion,
                )
                paso_guardado = self.repo_paso.guardar(paso_entidad)

                # Persistir hechos generados en este paso
                for hg in paso_res.hechos_generados:
                    hecho_inf = HechoInferido(
                        ejecucion_id=ejecucion.id,
                        paso_id=paso_guardado.id,
                        regla_origen_id=regla_id,
                        nombre=hg["nombre"],
                        valor=str(hg["valor"]),
                        tipo_dato=hg.get("tipo_dato", TipoDato.TEXTO.value),
                        procedencia=ProcedenciaHecho.DERIVADO.value,
                    )
                    self.repo_hecho_inf.guardar(hecho_inf)

                # Persistir conjunto de conflicto si hubo múltiples candidatas
                if paso_res.candidatas_conflicto and regla_id:
                    candidatas_entidades = []
                    for cand in paso_res.candidatas_conflicto:
                        es_sel = (cand.id == regla_id)
                        motivo = None if es_sel else paso_res.motivos_descarte_conflicto.get(cand.id)
                        candidatas_entidades.append(
                            ConflictoReglaCandidata(
                                regla_id=cand.id,
                                prioridad=cand.prioridad,
                                fue_seleccionada=es_sel,
                                motivo_descarte=motivo,
                            )
                        )
                    conflicto_entidad = ConflictoInferencia(
                        ejecucion_id=ejecucion.id,
                        paso_id=paso_guardado.id,
                        numero_paso=paso_res.numero_paso,
                        regla_seleccionada_id=regla_id,
                        criterio_aplicado=paso_res.criterio_conflicto,
                        explicacion_resolucion=paso_res.explicacion_conflicto,
                    )
                    self.repo_conflicto.guardar(conflicto_entidad, candidatas_entidades)

            # 3. Guardar explicación determinista (HU-17)
            explicacion_dict = MotorExplicabilidad.construir_explicacion(
                conclusion_final=resultado.conclusion_final,
                hechos_iniciales=resultado.hechos_iniciales,
                pasos=resultado.pasos,
            )
            explicacion_entidad = ExplicacionConclusion(
                ejecucion_id=ejecucion.id,
                conclusion=resultado.conclusion_final or "Sin conclusión",
                arbol_justificacion=explicacion_dict["arbol"],
                texto_explicativo=explicacion_dict["texto"],
            )
            self.repo_explicacion.guardar(explicacion_entidad)

            # 4. Actualizar ejecución como FINALIZADA
            ejecucion.estado = EstadoEjecucion.FINALIZADA
            ejecucion.fecha_fin = timezone.now()
            ejecucion.conclusion_final = resultado.conclusion_final
            ejecucion.paso_actual = len(resultado.pasos)
            if resultado.pasos:
                ejecucion.memoria_trabajo_snapshot = resultado.pasos[-1].memoria_trabajo_post
            self.repo_ejecucion.guardar(ejecucion)

            return resultado

        except Exception as e:
            ejecucion.estado = EstadoEjecucion.ERROR
            ejecucion.fecha_fin = timezone.now()
            ejecucion.conclusion_final = f"Error: {str(e)}"
            self.repo_ejecucion.guardar(ejecucion)
            raise


class IniciarSimulacion:
    """Inicia una sesión de simulación interactiva con hechos temporales o por defecto (HU-14)."""

    def __init__(
        self,
        repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None,
        repo_se: Optional[SistemaExpertoRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
        repo_hecho: Optional[HechoRepositorio] = None,
    ):
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()
        self.repo_se = repo_se or DjangoSistemaExpertoRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()

    def ejecutar(
        self,
        sistema_experto_id: UUID,
        hechos_iniciales_custom: Optional[List[Dict[str, Any]]] = None,
    ) -> EjecucionInferencia:
        se = self.repo_se.obtener_por_id(sistema_experto_id)
        if not se:
            raise SistemaExpertoNoEncontrado(sistema_experto_id)

        bc = self.repo_bc.obtener_por_sistema_experto_id(sistema_experto_id)
        if not bc:
            raise SistemaExpertoNoEncontrado(
                f"El sistema experto {sistema_experto_id} no tiene base de conocimiento."
            )

        # Cargar hechos base de la BC si no se enviaron hechos personalizados
        hechos_snapshot: List[Dict[str, Any]] = []
        memoria_inicial: Dict[str, Any] = {}

        if hechos_iniciales_custom is not None:
            for hp in hechos_iniciales_custom:
                nombre = hp.get("nombre")
                valor = hp.get("valor")
                tipo = hp.get("tipo_dato", TipoDato.TEXTO.value)
                parsed_val = MotorInferencia._parsear_valor_hecho(valor, tipo)
                if parsed_val is not None:
                    memoria_inicial[nombre] = parsed_val
                hechos_snapshot.append(
                    {"nombre": nombre, "valor": parsed_val, "tipo_dato": tipo}
                )
        else:
            hechos_db = self.repo_hecho.listar_por_base(bc.id)
            for h in hechos_db:
                parsed_val = MotorInferencia._parsear_valor_hecho(h.valor, h.tipo_dato)
                if parsed_val is not None:
                    memoria_inicial[h.nombre] = parsed_val
                hechos_snapshot.append(
                    {"nombre": h.nombre, "valor": parsed_val, "tipo_dato": str(h.tipo_dato)}
                )

        ejecucion = EjecucionInferencia(
            sistema_experto_id=sistema_experto_id,
            estado=EstadoEjecucion.INICIADA,
            modo=ModoInferencia.SIMULACION,
            paso_actual=0,
            memoria_trabajo_snapshot=memoria_inicial,
            hechos_iniciales_snapshot=hechos_snapshot,
            es_simulacion=True,
            recorrido_por_regla=nuevo_recorrido(memoria_inicial),
        )
        return self.repo_ejecucion.guardar(ejecucion)


class AvanzarPasoSimulacion:
    """Ejecuta incrementalmente un único paso de inferencia y actualiza el estado (HU-09, HU-15)."""

    def __init__(
        self,
        repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None,
        repo_paso: Optional[PasoInferenciaRepositorio] = None,
        repo_hecho_inf: Optional[HechoInferidoRepositorio] = None,
        repo_conflicto: Optional[ConflictoInferenciaRepositorio] = None,
        repo_explicacion: Optional[ExplicacionConclusionRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
        repo_hecho: Optional[HechoRepositorio] = None,
        repo_var: Optional[VariableRepositorio] = None,
        repo_regla: Optional[ReglaRepositorio] = None,
        repo_detalle: Optional[DetalleInferenciaRepositorio] = None,
    ):
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()
        self.repo_paso = repo_paso or DjangoPasoInferenciaRepositorio()
        self.repo_hecho_inf = repo_hecho_inf or DjangoHechoInferidoRepositorio()
        self.repo_conflicto = repo_conflicto or DjangoConflictoInferenciaRepositorio()
        self.repo_explicacion = repo_explicacion or DjangoExplicacionConclusionRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()
        self.repo_var = repo_var or DjangoVariableRepositorio()
        self.repo_regla = repo_regla or DjangoReglaRepositorio()
        self.repo_detalle = repo_detalle or DjangoDetalleInferenciaRepositorio()

    @transaction.atomic
    def ejecutar(
        self,
        id_ejecucion: UUID,
        hechos_nuevos: Optional[List[Dict[str, Any]]] = None,
        regla_id: Optional[UUID] = None,
        modo_evaluacion: Optional[str] = None,
    ) -> Dict[str, Any]:
        ejecucion = self.repo_ejecucion.obtener_por_id(id_ejecucion)
        if not ejecucion:
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)

        if ejecucion.estado in (EstadoEjecucion.FINALIZADA, EstadoEjecucion.ERROR):
            return {
                "finalizado": True,
                "mensaje": f"La ejecución ya se encuentra en estado {ejecucion.estado.value}.",
            }
        if ejecucion.estado == EstadoEjecucion.PAUSADA:
            return {"finalizado": False, "mensaje": "La simulación está pausada."}

        recorrido = copy.deepcopy(ejecucion.recorrido_por_regla) or nuevo_recorrido(ejecucion.memoria_trabajo_snapshot)
        if "contador_visual" not in (ejecucion.recorrido_por_regla or {}):
            recorrido["contador_visual"] = ejecucion.paso_actual
            recorrido["paso_visual_actual"] = ejecucion.paso_actual

        # Incorporar hechos respondidos interactivamente durante este paso
        if hechos_nuevos:
            memoria_actual = dict(ejecucion.memoria_trabajo_snapshot or {})
            for hn in hechos_nuevos:
                nombre = hn.get("nombre")
                valor = hn.get("valor")
                tipo = hn.get("tipo_dato", TipoDato.TEXTO.value)
                parsed_val = MotorInferencia._parsear_valor_hecho(valor, tipo)
                if parsed_val is None:
                    memoria_actual.pop(nombre, None)
                else:
                    memoria_actual[nombre] = parsed_val
            ejecucion.memoria_trabajo_snapshot = memoria_actual

        bc = self.repo_bc.obtener_por_sistema_experto_id(ejecucion.sistema_experto_id)
        if not bc:
            raise SistemaExpertoNoEncontrado(
                f"Sistema {ejecucion.sistema_experto_id} no tiene base de conocimiento."
            )

        variables = self.repo_var.listar_por_base(bc.id)
        reglas_activas = self.repo_regla.listar_activas_por_base(bc.id)
        hechos_iniciales = self.repo_hecho.listar_por_base(bc.id)
        if ejecucion.bc_snapshot:
            from apps.actividades.politicas import dominio_snapshot
            hechos_iniciales, variables, reglas_snapshot = dominio_snapshot(ejecucion.bc_snapshot)
            reglas_activas = [r for r in reglas_snapshot if r.activa]

        # Determinar reglas ya disparadas en pasos anteriores
        pasos_anteriores = self.repo_paso.listar_por_ejecucion(id_ejecucion)
        reglas_ejecutadas: Set[UUID] = {
            p.regla_disparada_id for p in pasos_anteriores if p.regla_disparada_id
        }

        mapa_ids = MotorInferencia.construir_mapa_ids(hechos_iniciales, reglas_activas, variables)
        nuevo_numero_paso = ejecucion.paso_actual + 1

        reglas_ordenadas = ordenar_reglas(reglas_activas)
        limite = getattr(settings, "MAX_INFERENCE_ITERATIONS", 100)
        if nuevo_numero_paso > limite * max(1, len(reglas_ordenadas)) or recorrido["numero_vuelta"] > limite:
            raise LimiteIteracionesAlcanzado(limite)

        regla_especifica = None
        es_recorrido = modo_evaluacion == "POR_REGLA" and not regla_id
        if regla_id:
            regla_especifica = next((r for r in reglas_ordenadas if str(r.id) == str(regla_id) and r.id not in reglas_ejecutadas), None)
        elif es_recorrido:
            recorrido, fin_recorrido = cerrar_vuelta(
                recorrido, ejecucion.memoria_trabajo_snapshot, reglas_activas, reglas_ejecutadas,
            )
            pendientes = pendientes_recorrido(reglas_activas, reglas_ejecutadas, recorrido)
            if pendientes and not fin_recorrido:
                regla_especifica = pendientes[0]

        motor = MotorInferencia()
        if regla_especifica is not None:
            resultado_paso = motor.ejecutar_un_paso_regla(
                memoria_trabajo=ejecucion.memoria_trabajo_snapshot,
                regla=regla_especifica,
                numero_paso=nuevo_numero_paso,
                variables=variables,
                mapa_ids_a_nombres=mapa_ids,
                es_ultimo_paso=False,
            )
        elif es_recorrido or regla_id:
            resultado_paso = PasoEjecucionResultado(
                numero_paso=nuevo_numero_paso, finalizado=True,
                memoria_trabajo_pre=dict(ejecucion.memoria_trabajo_snapshot),
                memoria_trabajo_post=dict(ejecucion.memoria_trabajo_snapshot),
                descripcion="Recorrido terminado: no quedan reglas pendientes en esta vuelta.",
            )
        else:
            resultado_paso = motor.ejecutar_un_paso(
                memoria_trabajo=ejecucion.memoria_trabajo_snapshot,
                reglas_ejecutadas=reglas_ejecutadas,
                reglas=reglas_activas,
                variables=variables,
                mapa_ids_a_nombres=mapa_ids,
                numero_paso=nuevo_numero_paso,
            )

        paso_visual = asignar_paso_visual(recorrido, es_recorrido, ejecucion.paso_actual)
        for traza in resultado_paso.trazas_paso:
            traza.paso_visual = paso_visual

        # Comparar la BH por sus tipos declarados: True y la conclusión "true"
        # representan el mismo valor booleano, no un cambio que justifique otra vuelta.
        tipos_por_nombre = {h.nombre: h.tipo_dato for h in hechos_iniciales}
        tipos_por_nombre.update({v.nombre: v.tipo_dato for v in variables})
        for nombre, valor in list(resultado_paso.memoria_trabajo_post.items()):
            tipo = tipos_por_nombre.get(nombre)
            if tipo is not None:
                valor = motor._parsear_valor_hecho(valor, tipo)
            elif isinstance(valor, str) and not valor.strip():
                valor = None
            if valor is None:
                resultado_paso.memoria_trabajo_post.pop(nombre, None)
            else:
                resultado_paso.memoria_trabajo_post[nombre] = valor

        regla_id_disparada = (
            resultado_paso.regla_disparada.id
            if resultado_paso.regla_disparada
            else None
        )
        if regla_id_disparada:
            reglas_ejecutadas.add(regla_id_disparada)
            recorrido["hubo_disparo"] = True
        if es_recorrido and regla_especifica is not None:
            recorrido["visitadas"].append(str(regla_especifica.id))
        if es_recorrido or (regla_id_disparada and not pendientes_recorrido(reglas_activas, reglas_ejecutadas, recorrido)):
            recorrido, resultado_paso.finalizado = cerrar_vuelta(
                recorrido, resultado_paso.memoria_trabajo_post, reglas_activas, reglas_ejecutadas,
            )
        ejecucion.recorrido_por_regla = recorrido

        # Persistir el paso
        paso_entidad = PasoInferencia(
            ejecucion_id=ejecucion.id,
            numero_paso=nuevo_numero_paso,
            regla_disparada_id=regla_id_disparada,
            memoria_trabajo_pre=resultado_paso.memoria_trabajo_pre,
            memoria_trabajo_post=resultado_paso.memoria_trabajo_post,
            descripcion=resultado_paso.descripcion,
        )
        paso_guardado = self.repo_paso.guardar(paso_entidad)

        # Persistir hechos inferidos en este paso
        for hg in resultado_paso.hechos_generados:
            hecho_inf = HechoInferido(
                ejecucion_id=ejecucion.id,
                paso_id=paso_guardado.id,
                regla_origen_id=regla_id_disparada,
                nombre=hg["nombre"],
                valor=str(hg["valor"]),
                procedencia=ProcedenciaHecho.DERIVADO.value,
            )
            self.repo_hecho_inf.guardar(hecho_inf)

        # Persistir conflicto si hubo reglas candidatas
        if resultado_paso.candidatas_conflicto and regla_id_disparada:
            candidatas_entidades = []
            for cand in resultado_paso.candidatas_conflicto:
                es_sel = (cand.id == regla_id_disparada)
                motivo = None if es_sel else resultado_paso.motivos_descarte_conflicto.get(cand.id)
                candidatas_entidades.append(
                    ConflictoReglaCandidata(
                        regla_id=cand.id,
                        prioridad=cand.prioridad,
                        fue_seleccionada=es_sel,
                        motivo_descarte=motivo,
                    )
                )
            conflicto_entidad = ConflictoInferencia(
                ejecucion_id=ejecucion.id,
                paso_id=paso_guardado.id,
                numero_paso=nuevo_numero_paso,
                regla_seleccionada_id=regla_id_disparada,
                criterio_aplicado=resultado_paso.criterio_conflicto,
                explicacion_resolucion=resultado_paso.explicacion_conflicto,
            )
            self.repo_conflicto.guardar(conflicto_entidad, candidatas_entidades)

        # Persistir detalles de traza para este paso (para que aparezcan las reglas evaluadas)
        trazas = getattr(resultado_paso, "trazas_paso", None) or getattr(resultado_paso, "trazas", None) or []
        if trazas:
            detalles_existentes = self.repo_detalle.listar_por_ejecucion(id_ejecucion)
            orden_base = len(detalles_existentes)
            detalles_entidades = [
                DetalleInferencia(
                    ejecucion_id=ejecucion.id,
                    regla_id=t.regla_id,
                    orden=orden_base + idx + 1,
                    estado_regla=t.estado,
                    condiciones_cumplidas=t.condiciones_cumplidas,
                    condiciones_evaluadas=t.condiciones_evaluadas,
                    paso_numero=t.paso_numero,
                    paso_visual=t.paso_visual,
                    resultado_generado=t.resultado_generado,
                )
                for idx, t in enumerate(trazas)
            ]
            self.repo_detalle.guardar_lote(detalles_entidades)

        # Actualizar ejecución
        ejecucion.paso_actual = nuevo_numero_paso
        ejecucion.memoria_trabajo_snapshot = resultado_paso.memoria_trabajo_post
        ejecucion.estado = EstadoEjecucion.EJECUTANDO

        if resultado_paso.finalizado:
            ejecucion.estado = EstadoEjecucion.FINALIZADA
            ejecucion.fecha_fin = timezone.now()
            # Conclusión final
            if resultado_paso.conclusion_final:
                ejecucion.conclusion_final = resultado_paso.conclusion_final
            else:
                # Revisar último hecho inferido si no vino conclusión explícita en este paso
                ultimos_hechos = self.repo_hecho_inf.listar_por_ejecucion(id_ejecucion)
                if ultimos_hechos:
                    ejecucion.conclusion_final = ultimos_hechos[-1].valor

            # Reconstruir explicación determinista con todos los pasos
            todos_los_pasos = self.repo_paso.listar_por_ejecucion(id_ejecucion)
            hechos_para_explicacion = ejecucion.hechos_iniciales_snapshot
            explicacion_dict = MotorExplicabilidad.construir_explicacion(
                conclusion_final=ejecucion.conclusion_final,
                hechos_iniciales=hechos_para_explicacion,
                pasos=todos_los_pasos,
            )
            explicacion_entidad = ExplicacionConclusion(
                ejecucion_id=ejecucion.id,
                conclusion=ejecucion.conclusion_final or "Sin conclusión",
                arbol_justificacion=explicacion_dict["arbol"],
                texto_explicativo=explicacion_dict["texto"],
            )
            self.repo_explicacion.guardar(explicacion_entidad)

        self.repo_ejecucion.guardar(ejecucion)

        from apps.inferencia.serializers import DetalleInferenciaSalidaSerializer
        detalles_actualizados = self.repo_detalle.listar_por_ejecucion(id_ejecucion)
        detalles_data = DetalleInferenciaSalidaSerializer(detalles_actualizados, many=True).data

        return {
            "id": str(ejecucion.id),
            "ejecucion_id": str(ejecucion.id),
            "paso_actual": ejecucion.paso_actual,
            "paso_visual_actual": paso_visual,
            "paso": paso_guardado,
            "finalizado": resultado_paso.finalizado,
            "hechos_generados": resultado_paso.hechos_generados,
            "memoria_trabajo": resultado_paso.memoria_trabajo_post,
            "conclusion_final": ejecucion.conclusion_final,
            "estado": ejecucion.estado.value,
            "reglas_evaluadas": detalles_data,
            "detalles": detalles_data,
        }


class ControlarSimulacion:
    """Gestiona pausas, reanudaciones, reinicios y paradas forzadas (HU-15)."""

    def __init__(
        self,
        repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None,
        avanzar_service: Optional[AvanzarPasoSimulacion] = None,
    ):
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()
        self.avanzar_service = avanzar_service or AvanzarPasoSimulacion()

    def pausar(self, id_ejecucion: UUID) -> EjecucionInferencia:
        ejecucion = self.repo_ejecucion.obtener_por_id(id_ejecucion)
        if not ejecucion:
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)
        if ejecucion.estado == EstadoEjecucion.FINALIZADA:
            return ejecucion
        ejecucion.estado = EstadoEjecucion.PAUSADA
        return self.repo_ejecucion.guardar(ejecucion)

    def continuar(self, id_ejecucion: UUID) -> EjecucionInferencia:
        ejecucion = self.repo_ejecucion.obtener_por_id(id_ejecucion)
        if not ejecucion:
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)
        if ejecucion.estado == EstadoEjecucion.PAUSADA:
            ejecucion.estado = EstadoEjecucion.EJECUTANDO
            return self.repo_ejecucion.guardar(ejecucion)

        # Ejecutar pasos hasta finalizar
        max_pasos = 100
        paso_count = 0
        while paso_count < max_pasos:
            res = self.avanzar_service.ejecutar(id_ejecucion)
            if res.get("finalizado"):
                break
            paso_count += 1
        return self.repo_ejecucion.obtener_por_id(id_ejecucion)

    def reiniciar(self, id_ejecucion: UUID) -> EjecucionInferencia:
        ejecucion = self.repo_ejecucion.obtener_por_id(id_ejecucion)
        if not ejecucion:
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)

        # Restaurar memoria inicial
        memoria_restaurada: Dict[str, Any] = {}
        for h in (ejecucion.hechos_iniciales_snapshot or []):
            valor = MotorInferencia._parsear_valor_hecho(h.get("valor"), h.get("tipo_dato", TipoDato.TEXTO))
            if valor is not None:
                memoria_restaurada[h["nombre"]] = valor

        # Limpiar registros asociados a los pasos previos para reiniciar limpiamente desde 0
        from apps.inferencia.models import (
            PasoInferenciaModel,
            HechoInferidoModel,
            ConflictoInferenciaModel,
            DetalleInferenciaModel,
            ExplicacionConclusionModel,
        )
        PasoInferenciaModel.objects.filter(ejecucion_id=id_ejecucion).delete()
        HechoInferidoModel.objects.filter(ejecucion_id=id_ejecucion).delete()
        ConflictoInferenciaModel.objects.filter(ejecucion_id=id_ejecucion).delete()
        DetalleInferenciaModel.objects.filter(ejecucion_id=id_ejecucion).delete()
        ExplicacionConclusionModel.objects.filter(ejecucion_id=id_ejecucion).delete()

        ejecucion.paso_actual = 0
        ejecucion.memoria_trabajo_snapshot = memoria_restaurada
        ejecucion.recorrido_por_regla = nuevo_recorrido(memoria_restaurada)
        ejecucion.estado = EstadoEjecucion.INICIADA
        ejecucion.conclusion_final = None
        ejecucion.factor_certeza_final = None
        ejecucion.fecha_fin = None
        ejecucion.arbol_deduccion = None
        ejecucion.explicabilidad = None
        return self.repo_ejecucion.guardar(ejecucion)

    def finalizar(self, id_ejecucion: UUID) -> EjecucionInferencia:
        ejecucion = self.repo_ejecucion.obtener_por_id(id_ejecucion)
        if not ejecucion:
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)
        ejecucion.estado = EstadoEjecucion.FINALIZADA
        ejecucion.fecha_fin = timezone.now()
        return self.repo_ejecucion.guardar(ejecucion)


class ConsultarEjecucion:
    def __init__(self, repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None):
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()

    def ejecutar(self, id_ejecucion: UUID) -> EjecucionInferencia:
        ejecucion = self.repo_ejecucion.obtener_por_id(id_ejecucion)
        if not ejecucion:
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)
        return ejecucion


class ConsultarHistorialInferencia:
    """Consulta el historial persistente de ejecuciones de inferencia con filtros (HU-16)."""

    def __init__(self, repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None):
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()

    def ejecutar(
        self,
        sistema_experto_id: Optional[UUID] = None,
        estado: Optional[str] = None,
        modo: Optional[str] = None,
        excluir_borradores: bool = False,
        asignacion_id: Optional[UUID] = None,
        estudiante_id: Optional[int] = None,
    ) -> List[EjecucionInferencia]:
        return self.repo_ejecucion.listar_todas(
            id_sistema=sistema_experto_id,
            estado=estado,
            modo=modo,
            excluir_borradores=excluir_borradores,
            asignacion_id=asignacion_id,
            estudiante_id=estudiante_id,
        )


class ConsultarExplicacionConclusion:
    """Consulta la explicación y árbol causal de una ejecución (HU-17)."""

    def __init__(
        self,
        repo_explicacion: Optional[ExplicacionConclusionRepositorio] = None,
        repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None,
        repo_paso: Optional[PasoInferenciaRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
        repo_regla: Optional[ReglaRepositorio] = None,
        repo_hecho: Optional[HechoRepositorio] = None,
        repo_var: Optional[VariableRepositorio] = None,
        repo_hecho_inf: Optional[HechoInferidoRepositorio] = None,
        repo_detalle: Optional[DetalleInferenciaRepositorio] = None,
    ):
        self.repo_explicacion = repo_explicacion or DjangoExplicacionConclusionRepositorio()
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()
        self.repo_paso = repo_paso or DjangoPasoInferenciaRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()
        self.repo_regla = repo_regla or DjangoReglaRepositorio()
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()
        self.repo_var = repo_var or DjangoVariableRepositorio()
        self.repo_hecho_inf = repo_hecho_inf or DjangoHechoInferidoRepositorio()
        self.repo_detalle = repo_detalle or DjangoDetalleInferenciaRepositorio()

    def ejecutar(self, id_ejecucion: UUID) -> Dict[str, Any]:
        ejecucion = self.repo_ejecucion.obtener_por_id(id_ejecucion)
        if not ejecucion:
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)

        exp = self.repo_explicacion.obtener_por_ejecucion(id_ejecucion)
        legacy = None
        if exp:
            legacy = {
                "conclusion": exp.conclusion,
                "texto": exp.texto_explicativo,
                "arbol": exp.arbol_justificacion,
            }

        # Enriquecer también explicaciones antiguas: sus tres campos persistidos
        # no contienen las reglas, condiciones y hechos que necesita la consulta.
        pasos = self.repo_paso.listar_por_ejecucion(id_ejecucion)
        base = self.repo_bc.obtener_por_sistema_experto_id(ejecucion.sistema_experto_id)
        reglas = self.repo_regla.listar_por_base(base.id) if base else []
        hechos = self.repo_hecho.listar_por_base(base.id) if base else []
        variables = self.repo_var.listar_por_base(base.id) if base else []
        if ejecucion.bc_snapshot:
            from apps.actividades.politicas import dominio_snapshot
            hechos, variables, reglas = dominio_snapshot(ejecucion.bc_snapshot)
        nombres = MotorInferencia.construir_mapa_ids(hechos, reglas, variables)
        return MotorExplicabilidad.construir_explicacion_detallada(
            conclusion_final=ejecucion.conclusion_final,
            hechos_iniciales=ejecucion.hechos_iniciales_snapshot,
            pasos=pasos,
            reglas=reglas,
            nombres=nombres,
            hechos_generados=self.repo_hecho_inf.listar_por_ejecucion(id_ejecucion),
            detalles=self.repo_detalle.listar_por_ejecucion(id_ejecucion),
            explicacion_legacy=legacy,
        )


class ConsultarConflictosEjecucion:
    """Consulta los conjuntos de conflicto registrados durante una inferencia (HU-13)."""

    def __init__(
        self,
        repo_conflicto: Optional[ConflictoInferenciaRepositorio] = None,
        repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None,
    ):
        self.repo_conflicto = repo_conflicto or DjangoConflictoInferenciaRepositorio()
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()

    def ejecutar(self, id_ejecucion: UUID) -> List[ConflictoInferencia]:
        if not self.repo_ejecucion.obtener_por_id(id_ejecucion):
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)
        return self.repo_conflicto.listar_por_ejecucion(id_ejecucion)


class ConsultarHechosInferidos:
    """Consulta los hechos generados / deducidos en una ejecución (HU-12)."""

    def __init__(
        self,
        repo_hecho_inf: Optional[HechoInferidoRepositorio] = None,
        repo_ejecucion: Optional[EjecucionInferenciaRepositorio] = None,
    ):
        self.repo_hecho_inf = repo_hecho_inf or DjangoHechoInferidoRepositorio()
        self.repo_ejecucion = repo_ejecucion or DjangoEjecucionInferenciaRepositorio()

    def ejecutar(
        self, id_ejecucion: UUID, procedencia: Optional[str] = None
    ) -> List[HechoInferido]:
        if not self.repo_ejecucion.obtener_por_id(id_ejecucion):
            raise EjecucionInferenciaNoEncontrada(id_ejecucion)
        return self.repo_hecho_inf.listar_por_ejecucion(id_ejecucion, procedencia=procedencia)


class ConsultarTrazaInferencia:
    """Consulta las trazas de detalle por regla (Sprint 1)."""

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
