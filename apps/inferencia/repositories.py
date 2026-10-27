"""
Repositorios para el módulo de Inferencia (Sprint 1 + Sprint 2).
Incluye interfaces abstractas y adaptadores concretos con Django ORM para:
- EjecucionInferencia
- DetalleInferencia
- PasoInferencia
- HechoInferido
- ConflictoInferencia
- ExplicacionConclusion
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID
from django.db.models import Count, Q
from django.db.models.functions import Coalesce

from apps.inferencia.entities import (
    ConflictoInferencia,
    ConflictoReglaCandidata,
    DetalleInferencia,
    EjecucionInferencia,
    ExplicacionConclusion,
    HechoInferido,
    PasoInferencia,
)
from apps.inferencia.models import (
    ConflictoInferenciaModel,
    ConflictoReglaCandidataModel,
    DetalleInferenciaModel,
    EjecucionInferenciaModel,
    ExplicacionConclusionModel,
    HechoInferidoModel,
    PasoInferenciaModel,
)
from compartido.constantes.enums import (
    EstadoEjecucion,
    EstadoReglaInferencia,
    ModoInferencia,
    ProcedenciaHecho,
    TipoDato,
)


class EjecucionInferenciaRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_ejecucion: UUID) -> Optional[EjecucionInferencia]:
        pass

    @abstractmethod
    def listar_por_sistema(
        self, id_sistema: UUID, modo: Optional[str] = None
    ) -> List[EjecucionInferencia]:
        pass

    @abstractmethod
    def listar_todas(
        self,
        id_sistema: Optional[UUID] = None,
        estado: Optional[str] = None,
        modo: Optional[str] = None,
        excluir_borradores: bool = False,
        asignacion_id: Optional[UUID] = None,
        estudiante_id: Optional[int] = None,
    ) -> List[EjecucionInferencia]:
        pass

    @abstractmethod
    def guardar(self, ejecucion: EjecucionInferencia) -> EjecucionInferencia:
        pass


class DetalleInferenciaRepositorio(ABC):
    @abstractmethod
    def listar_por_ejecucion(self, id_ejecucion: UUID) -> List[DetalleInferencia]:
        pass

    @abstractmethod
    def guardar(self, detalle: DetalleInferencia) -> DetalleInferencia:
        pass

    @abstractmethod
    def guardar_lote(self, detalles: List[DetalleInferencia]) -> List[DetalleInferencia]:
        pass


class PasoInferenciaRepositorio(ABC):
    @abstractmethod
    def listar_por_ejecucion(self, id_ejecucion: UUID) -> List[PasoInferencia]:
        pass

    @abstractmethod
    def obtener_ultimo_paso(self, id_ejecucion: UUID) -> Optional[PasoInferencia]:
        pass

    @abstractmethod
    def guardar(self, paso: PasoInferencia) -> PasoInferencia:
        pass


class HechoInferidoRepositorio(ABC):
    @abstractmethod
    def listar_por_ejecucion(
        self, id_ejecucion: UUID, procedencia: Optional[str] = None
    ) -> List[HechoInferido]:
        pass

    @abstractmethod
    def guardar(self, hecho: HechoInferido) -> HechoInferido:
        pass

    @abstractmethod
    def guardar_lote(self, hechos: List[HechoInferido]) -> List[HechoInferido]:
        pass


class ConflictoInferenciaRepositorio(ABC):
    @abstractmethod
    def listar_por_ejecucion(self, id_ejecucion: UUID) -> List[ConflictoInferencia]:
        pass

    @abstractmethod
    def guardar(
        self, conflicto: ConflictoInferencia, candidatas: List[ConflictoReglaCandidata]
    ) -> ConflictoInferencia:
        pass


class ExplicacionConclusionRepositorio(ABC):
    @abstractmethod
    def obtener_por_ejecucion(self, id_ejecucion: UUID) -> Optional[ExplicacionConclusion]:
        pass

    @abstractmethod
    def guardar(self, explicacion: ExplicacionConclusion) -> ExplicacionConclusion:
        pass


# ============================================================================
# IMPLEMENTACIONES CON DJANGO ORM
# ============================================================================

class DjangoEjecucionInferenciaRepositorio(EjecucionInferenciaRepositorio):

    @staticmethod
    def _a_entidad(m: EjecucionInferenciaModel) -> EjecucionInferencia:
        return EjecucionInferencia(
            id=m.id,
            asignacion_id=m.asignacion_id,
            estudiante_id=m.estudiante_id,
            bc_snapshot=m.bc_snapshot or {},
            sistema_experto_id=m.sistema_experto_id,
            estado=EstadoEjecucion(m.estado),
            modo=ModoInferencia(m.modo) if hasattr(ModoInferencia, m.modo) else ModoInferencia.AUTOMATICA,
            paso_actual=m.paso_actual,
            memoria_trabajo_snapshot=m.memoria_trabajo_snapshot or {},
            hechos_iniciales_snapshot=m.hechos_iniciales_snapshot or [],
            recorrido_por_regla=m.recorrido_por_regla or {},
            es_simulacion=m.es_simulacion,
            fecha_inicio=m.fecha_inicio,
            fecha_fin=m.fecha_fin,
            conclusion_final=m.conclusion_final,
        )

    def obtener_por_id(self, id_ejecucion: UUID) -> Optional[EjecucionInferencia]:
        try:
            return self._a_entidad(EjecucionInferenciaModel.objects.get(id=id_ejecucion))
        except EjecucionInferenciaModel.DoesNotExist:
            return None

    def listar_por_sistema(
        self, id_sistema: UUID, modo: Optional[str] = None
    ) -> List[EjecucionInferencia]:
        return self.listar_todas(id_sistema=id_sistema, modo=modo)

    def listar_todas(
        self,
        id_sistema: Optional[UUID] = None,
        estado: Optional[str] = None,
        modo: Optional[str] = None,
        excluir_borradores: bool = False,
        asignacion_id: Optional[UUID] = None,
        estudiante_id: Optional[int] = None,
    ) -> List[EjecucionInferencia]:
        qs = EjecucionInferenciaModel.objects.all()
        if asignacion_id is not None and estudiante_id is not None:
            qs = qs.filter(asignacion_id=asignacion_id, estudiante_id=estudiante_id)
        else:
            qs = qs.filter(asignacion_id__isnull=True, sistema_experto__trabajo_actividad__isnull=True)
        if excluir_borradores:
            qs = qs.exclude(sistema_experto__estado="BORRADOR").filter(sistema_experto__actividades__isnull=True)
        if id_sistema:
            qs = qs.filter(sistema_experto_id=id_sistema)
        if estado:
            qs = qs.filter(estado=estado)
        if modo == "DIRECTO":
            qs = qs.filter(es_simulacion=False)
        elif modo == "SIMULACION_PASO_A_PASO":
            qs = qs.filter(es_simulacion=True)
        elif modo:
            qs = qs.filter(modo=modo)
        modelos = list(qs.annotate(
            pasos_fisicos=Count("pasos", distinct=True),
            disparadas=Count("pasos", filter=Q(pasos__regla_disparada_id__isnull=False), distinct=True),
        ).order_by("-fecha_inicio"))
        if not modelos:
            return []
        # Dos consultas para toda la lista: no contar filas de ACTIVADA/RECHAZADA
        # como nuevas evaluaciones ni clics pequeños como nuevos pasos visuales.
        resumenes = {
            fila["ejecucion_id"]: fila
            for fila in DetalleInferenciaModel.objects.filter(ejecucion_id__in=[m.id for m in modelos])
            .values("ejecucion_id").annotate(
                pasos=Count(Coalesce("paso_visual", "paso_numero"), distinct=True),
                evaluadas=Count("id", filter=Q(estado_regla="EVALUADA")),
            )
        }
        entidades = []
        for modelo in modelos:
            entidad = self._a_entidad(modelo)
            resumen = resumenes.get(modelo.id, {})
            entidad.total_pasos = resumen.get("pasos") or modelo.pasos_fisicos
            entidad.total_reglas_evaluadas = resumen.get("evaluadas", 0)
            entidad.total_reglas_disparadas = modelo.disparadas
            entidades.append(entidad)
        return entidades

    def guardar(self, ejecucion: EjecucionInferencia) -> EjecucionInferencia:
        estado_val = (
            ejecucion.estado.value
            if hasattr(ejecucion.estado, "value")
            else ejecucion.estado
        )
        modo_val = (
            ejecucion.modo.value
            if hasattr(ejecucion.modo, "value")
            else ejecucion.modo
        )
        m, _ = EjecucionInferenciaModel.objects.update_or_create(
            id=ejecucion.id,
            defaults={
                "sistema_experto_id": ejecucion.sistema_experto_id,
                "asignacion_id": ejecucion.asignacion_id,
                "estudiante_id": ejecucion.estudiante_id,
                "bc_snapshot": ejecucion.bc_snapshot,
                "estado": estado_val,
                "modo": modo_val,
                "paso_actual": ejecucion.paso_actual,
                "memoria_trabajo_snapshot": ejecucion.memoria_trabajo_snapshot,
                "hechos_iniciales_snapshot": ejecucion.hechos_iniciales_snapshot,
                "recorrido_por_regla": ejecucion.recorrido_por_regla,
                "es_simulacion": ejecucion.es_simulacion,
                "fecha_fin": ejecucion.fecha_fin,
                "conclusion_final": ejecucion.conclusion_final,
            },
        )
        return self._a_entidad(m)


class DjangoDetalleInferenciaRepositorio(DetalleInferenciaRepositorio):

    @staticmethod
    def _a_entidad(m: DetalleInferenciaModel) -> DetalleInferencia:
        return DetalleInferencia(
            id=m.id,
            ejecucion_id=m.ejecucion_id,
            regla_id=m.regla_id,
            orden=m.orden,
            estado_regla=EstadoReglaInferencia(m.estado_regla),
            condiciones_cumplidas=m.condiciones_cumplidas,
            condiciones_evaluadas=m.condiciones_evaluadas,
            paso_numero=m.paso_numero,
            paso_visual=m.paso_visual,
            resultado_generado=m.resultado_generado,
        )

    def listar_por_ejecucion(self, id_ejecucion: UUID) -> List[DetalleInferencia]:
        modelos = DetalleInferenciaModel.objects.filter(
            ejecucion_id=id_ejecucion
        ).order_by("orden")
        return [self._a_entidad(m) for m in modelos]

    def guardar(self, detalle: DetalleInferencia) -> DetalleInferencia:
        estado_val = (
            detalle.estado_regla.value
            if hasattr(detalle.estado_regla, "value")
            else detalle.estado_regla
        )
        m, _ = DetalleInferenciaModel.objects.update_or_create(
            id=detalle.id,
            defaults={
                "ejecucion_id": detalle.ejecucion_id,
                "regla_id": detalle.regla_id,
                "orden": detalle.orden,
                "estado_regla": estado_val,
                "condiciones_cumplidas": detalle.condiciones_cumplidas,
                "condiciones_evaluadas": detalle.condiciones_evaluadas,
                "paso_numero": detalle.paso_numero,
                "paso_visual": detalle.paso_visual,
                "resultado_generado": detalle.resultado_generado,
            },
        )
        return self._a_entidad(m)

    def guardar_lote(self, detalles: List[DetalleInferencia]) -> List[DetalleInferencia]:
        modelos = [
            DetalleInferenciaModel(
                id=d.id,
                ejecucion_id=d.ejecucion_id,
                regla_id=d.regla_id,
                orden=d.orden,
                estado_regla=(
                    d.estado_regla.value
                    if hasattr(d.estado_regla, "value")
                    else d.estado_regla
                ),
                condiciones_cumplidas=d.condiciones_cumplidas,
                condiciones_evaluadas=d.condiciones_evaluadas,
                paso_numero=d.paso_numero,
                paso_visual=d.paso_visual,
                resultado_generado=d.resultado_generado,
            )
            for d in detalles
        ]
        DetalleInferenciaModel.objects.bulk_create(modelos, ignore_conflicts=True)
        return detalles


class DjangoPasoInferenciaRepositorio(PasoInferenciaRepositorio):

    @staticmethod
    def _a_entidad(m: PasoInferenciaModel) -> PasoInferencia:
        return PasoInferencia(
            id=m.id,
            ejecucion_id=m.ejecucion_id,
            numero_paso=m.numero_paso,
            regla_disparada_id=m.regla_disparada_id,
            regla_nombre=m.regla_disparada.nombre if m.regla_disparada else None,
            memoria_trabajo_pre=m.memoria_trabajo_pre or {},
            memoria_trabajo_post=m.memoria_trabajo_post or {},
            descripcion=m.descripcion,
            fecha_ejecucion=m.fecha_ejecucion,
        )

    def listar_por_ejecucion(self, id_ejecucion: UUID) -> List[PasoInferencia]:
        qs = PasoInferenciaModel.objects.filter(
            ejecucion_id=id_ejecucion
        ).select_related("regla_disparada").order_by("numero_paso")
        return [self._a_entidad(m) for m in qs]

    def obtener_ultimo_paso(self, id_ejecucion: UUID) -> Optional[PasoInferencia]:
        m = (
            PasoInferenciaModel.objects.filter(ejecucion_id=id_ejecucion)
            .select_related("regla_disparada")
            .order_by("-numero_paso")
            .first()
        )
        return self._a_entidad(m) if m else None

    def guardar(self, paso: PasoInferencia) -> PasoInferencia:
        m, _ = PasoInferenciaModel.objects.update_or_create(
            ejecucion_id=paso.ejecucion_id,
            numero_paso=paso.numero_paso,
            defaults={
                "regla_disparada_id": paso.regla_disparada_id,
                "memoria_trabajo_pre": paso.memoria_trabajo_pre,
                "memoria_trabajo_post": paso.memoria_trabajo_post,
                "descripcion": paso.descripcion,
            },
        )
        return self._a_entidad(m)


class DjangoHechoInferidoRepositorio(HechoInferidoRepositorio):

    @staticmethod
    def _a_entidad(m: HechoInferidoModel) -> HechoInferido:
        return HechoInferido(
            id=m.id,
            ejecucion_id=m.ejecucion_id,
            paso_id=m.paso_id,
            regla_origen_id=m.regla_origen_id,
            regla_origen_nombre=m.regla_origen.nombre if m.regla_origen else None,
            nombre=m.nombre,
            valor=m.valor,
            tipo_dato=m.tipo_dato,
            procedencia=m.procedencia,
            orden=m.orden,
            creado_en=m.creado_en,
        )

    def listar_por_ejecucion(
        self, id_ejecucion: UUID, procedencia: Optional[str] = None
    ) -> List[HechoInferido]:
        qs = HechoInferidoModel.objects.filter(
            ejecucion_id=id_ejecucion
        ).select_related("regla_origen").order_by("orden")
        if procedencia:
            qs = qs.filter(procedencia=procedencia)
        return [self._a_entidad(m) for m in qs]

    def guardar(self, hecho: HechoInferido) -> HechoInferido:
        m, _ = HechoInferidoModel.objects.update_or_create(
            id=hecho.id,
            defaults={
                "ejecucion_id": hecho.ejecucion_id,
                "paso_id": hecho.paso_id,
                "regla_origen_id": hecho.regla_origen_id,
                "nombre": hecho.nombre,
                "valor": hecho.valor,
                "tipo_dato": hecho.tipo_dato,
                "procedencia": hecho.procedencia,
                "orden": hecho.orden,
            },
        )
        return self._a_entidad(m)

    def guardar_lote(self, hechos: List[HechoInferido]) -> List[HechoInferido]:
        modelos = [
            HechoInferidoModel(
                id=h.id,
                ejecucion_id=h.ejecucion_id,
                paso_id=h.paso_id,
                regla_origen_id=h.regla_origen_id,
                nombre=h.nombre,
                valor=h.valor,
                tipo_dato=h.tipo_dato,
                procedencia=h.procedencia,
                orden=h.orden,
            )
            for h in hechos
        ]
        HechoInferidoModel.objects.bulk_create(modelos, ignore_conflicts=True)
        return hechos


class DjangoConflictoInferenciaRepositorio(ConflictoInferenciaRepositorio):

    def listar_por_ejecucion(self, id_ejecucion: UUID) -> List[ConflictoInferencia]:
        qs = ConflictoInferenciaModel.objects.filter(
            ejecucion_id=id_ejecucion
        ).select_related("regla_seleccionada").prefetch_related("reglas_candidatas__regla").order_by("numero_paso")

        resultados: List[ConflictoInferencia] = []
        for m in qs:
            candidatas = [
                ConflictoReglaCandidata(
                    id=c.id,
                    conflicto_id=c.conflicto_id,
                    regla_id=c.regla_id,
                    regla_nombre=c.regla.nombre if c.regla else "",
                    prioridad=c.prioridad,
                    fue_seleccionada=c.fue_seleccionada,
                    motivo_descarte=c.motivo_descarte,
                )
                for c in m.reglas_candidatas.all()
            ]
            resultados.append(
                ConflictoInferencia(
                    id=m.id,
                    ejecucion_id=m.ejecucion_id,
                    paso_id=m.paso_id,
                    numero_paso=m.numero_paso,
                    regla_seleccionada_id=m.regla_seleccionada_id,
                    regla_seleccionada_nombre=m.regla_seleccionada.nombre if m.regla_seleccionada else "",
                    criterio_aplicado=m.criterio_aplicado,
                    explicacion_resolucion=m.explicacion_resolucion,
                    reglas_candidatas=candidatas,
                    creado_en=m.creado_en,
                )
            )
        return resultados

    def guardar(
        self, conflicto: ConflictoInferencia, candidatas: List[ConflictoReglaCandidata]
    ) -> ConflictoInferencia:
        m, _ = ConflictoInferenciaModel.objects.update_or_create(
            id=conflicto.id,
            defaults={
                "ejecucion_id": conflicto.ejecucion_id,
                "paso_id": conflicto.paso_id,
                "numero_paso": conflicto.numero_paso,
                "regla_seleccionada_id": conflicto.regla_seleccionada_id,
                "criterio_aplicado": conflicto.criterio_aplicado,
                "explicacion_resolucion": conflicto.explicacion_resolucion,
            },
        )
        candidatas_modelos = [
            ConflictoReglaCandidataModel(
                id=c.id,
                conflicto_id=m.id,
                regla_id=c.regla_id,
                prioridad=c.prioridad,
                fue_seleccionada=c.fue_seleccionada,
                motivo_descarte=c.motivo_descarte,
            )
            for c in candidatas
        ]
        ConflictoReglaCandidataModel.objects.bulk_create(candidatas_modelos, ignore_conflicts=True)
        conflicto.reglas_candidatas = candidatas
        return conflicto


class DjangoExplicacionConclusionRepositorio(ExplicacionConclusionRepositorio):

    @staticmethod
    def _a_entidad(m: ExplicacionConclusionModel) -> ExplicacionConclusion:
        return ExplicacionConclusion(
            id=m.id,
            ejecucion_id=m.ejecucion_id,
            conclusion=m.conclusion,
            arbol_justificacion=m.arbol_justificacion or {},
            texto_explicativo=m.texto_explicativo,
            creada_en=m.creada_en,
        )

    def obtener_por_ejecucion(self, id_ejecucion: UUID) -> Optional[ExplicacionConclusion]:
        try:
            m = ExplicacionConclusionModel.objects.get(ejecucion_id=id_ejecucion)
            return self._a_entidad(m)
        except ExplicacionConclusionModel.DoesNotExist:
            return None

    def guardar(self, explicacion: ExplicacionConclusion) -> ExplicacionConclusion:
        m, _ = ExplicacionConclusionModel.objects.update_or_create(
            id=explicacion.id,
            defaults={
                "ejecucion_id": explicacion.ejecucion_id,
                "conclusion": explicacion.conclusion,
                "arbol_justificacion": explicacion.arbol_justificacion,
                "texto_explicativo": explicacion.texto_explicativo,
            },
        )
        return self._a_entidad(m)
