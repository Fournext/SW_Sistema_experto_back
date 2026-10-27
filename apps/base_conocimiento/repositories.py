"""
Repositorios para el módulo de Base de Conocimiento.
Incluye interfaces abstractas y adaptadores con Django ORM.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from apps.base_conocimiento.entities import (
    BaseConocimiento,
    Conclusion,
    Condicion,
    Hecho,
    Regla,
    Variable,
)
from apps.base_conocimiento.models import (
    BaseConocimientoModel,
    ConclusionModel,
    CondicionModel,
    HechoModel,
    ReglaModel,
    VariableModel,
)
from compartido.constantes.enums import OperadorCondicion, TipoDato


# =====================================================================
# INTERFACES ABSTRACTAS
# =====================================================================

class BaseConocimientoRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_base: UUID) -> Optional[BaseConocimiento]:
        pass

    @abstractmethod
    def obtener_por_sistema_experto_id(self, id_sistema: UUID) -> Optional[BaseConocimiento]:
        pass

    @abstractmethod
    def guardar(self, base: BaseConocimiento) -> BaseConocimiento:
        pass


class HechoRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_hecho: UUID) -> Optional[Hecho]:
        pass

    @abstractmethod
    def listar_por_base(self, id_base: UUID) -> List[Hecho]:
        pass

    @abstractmethod
    def existe_nombre_en_base(
        self, id_base: UUID, nombre: str, excluir_id: Optional[UUID] = None
    ) -> bool:
        pass

    @abstractmethod
    def guardar(self, hecho: Hecho) -> Hecho:
        pass

    @abstractmethod
    def eliminar(self, id_hecho: UUID) -> bool:
        pass


class VariableRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_variable: UUID) -> Optional[Variable]:
        pass

    @abstractmethod
    def listar_por_base(self, id_base: UUID) -> List[Variable]:
        pass

    @abstractmethod
    def existe_nombre_en_base(
        self, id_base: UUID, nombre: str, excluir_id: Optional[UUID] = None
    ) -> bool:
        pass

    @abstractmethod
    def guardar(self, variable: Variable) -> Variable:
        pass

    @abstractmethod
    def eliminar(self, id_variable: UUID) -> bool:
        pass


class ReglaRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_regla: UUID) -> Optional[Regla]:
        pass

    @abstractmethod
    def listar_por_base(self, id_base: UUID) -> List[Regla]:
        pass

    @abstractmethod
    def listar_activas_por_base(self, id_base: UUID) -> List[Regla]:
        pass

    @abstractmethod
    def existe_nombre_en_base(
        self, id_base: UUID, nombre: str, excluir_id: Optional[UUID] = None
    ) -> bool:
        pass

    @abstractmethod
    def guardar(self, regla: Regla) -> Regla:
        pass

    @abstractmethod
    def eliminar(self, id_regla: UUID) -> bool:
        pass


class CondicionRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_condicion: UUID) -> Optional[Condicion]:
        pass

    @abstractmethod
    def listar_por_regla(self, id_regla: UUID) -> List[Condicion]:
        pass

    @abstractmethod
    def guardar(self, condicion: Condicion) -> Condicion:
        pass

    @abstractmethod
    def eliminar(self, id_condicion: UUID) -> bool:
        pass


class ConclusionRepositorio(ABC):
    @abstractmethod
    def obtener_por_id(self, id_conclusion: UUID) -> Optional[Conclusion]:
        pass

    @abstractmethod
    def listar_por_regla(self, id_regla: UUID) -> List[Conclusion]:
        pass

    @abstractmethod
    def guardar(self, conclusion: Conclusion) -> Conclusion:
        pass

    @abstractmethod
    def eliminar(self, id_conclusion: UUID) -> bool:
        pass


# =====================================================================
# IMPLEMENTACIONES CON DJANGO ORM
# =====================================================================

class DjangoBaseConocimientoRepositorio(BaseConocimientoRepositorio):

    @staticmethod
    def _a_entidad(m: BaseConocimientoModel) -> BaseConocimiento:
        return BaseConocimiento(
            id=m.id,
            sistema_experto_id=m.sistema_experto_id,
            nombre=m.nombre,
            version=m.version,
            creada_en=m.creada_en,
            actualizada_en=m.actualizada_en,
        )

    def obtener_por_id(self, id_base: UUID) -> Optional[BaseConocimiento]:
        try:
            m = BaseConocimientoModel.objects.get(id=id_base)
            return self._a_entidad(m)
        except BaseConocimientoModel.DoesNotExist:
            return None

    def obtener_por_sistema_experto_id(self, id_sistema: UUID) -> Optional[BaseConocimiento]:
        try:
            m = BaseConocimientoModel.objects.get(sistema_experto_id=id_sistema)
            return self._a_entidad(m)
        except BaseConocimientoModel.DoesNotExist:
            return None

    def guardar(self, base: BaseConocimiento) -> BaseConocimiento:
        m, _ = BaseConocimientoModel.objects.update_or_create(
            id=base.id,
            defaults={
                "sistema_experto_id": base.sistema_experto_id,
                "nombre": base.nombre,
                "version": base.version,
            },
        )
        return self._a_entidad(m)


class DjangoHechoRepositorio(HechoRepositorio):

    @staticmethod
    def _a_entidad(m: HechoModel) -> Hecho:
        return Hecho(
            id=m.id,
            base_conocimiento_id=m.base_conocimiento_id,
            nombre=m.nombre,
            valor=m.valor,
            tipo_dato=TipoDato(m.tipo_dato),
            opciones=m.opciones or [],
            pregunta=m.pregunta,
            es_inicial=m.es_inicial,
        )

    def obtener_por_id(self, id_hecho: UUID) -> Optional[Hecho]:
        try:
            return self._a_entidad(HechoModel.objects.get(id=id_hecho))
        except HechoModel.DoesNotExist:
            return None

    def listar_por_base(self, id_base: UUID) -> List[Hecho]:
        return [
            self._a_entidad(m)
            for m in HechoModel.objects.filter(base_conocimiento_id=id_base).order_by("nombre")
        ]

    def existe_nombre_en_base(
        self, id_base: UUID, nombre: str, excluir_id: Optional[UUID] = None
    ) -> bool:
        qs = HechoModel.objects.filter(base_conocimiento_id=id_base, nombre__iexact=nombre)
        if excluir_id:
            qs = qs.exclude(id=excluir_id)
        return qs.exists()

    def guardar(self, hecho: Hecho) -> Hecho:
        m, _ = HechoModel.objects.update_or_create(
            id=hecho.id,
            defaults={
                "base_conocimiento_id": hecho.base_conocimiento_id,
                "nombre": hecho.nombre,
                "valor": hecho.valor,
                "tipo_dato": (
                    hecho.tipo_dato.value
                    if hasattr(hecho.tipo_dato, "value")
                    else hecho.tipo_dato
                ),
                "opciones": hecho.opciones or [],
                "pregunta": hecho.pregunta,
                "es_inicial": hecho.es_inicial,
            },
        )
        return self._a_entidad(m)

    def eliminar(self, id_hecho: UUID) -> bool:
        filas, _ = HechoModel.objects.filter(id=id_hecho).delete()
        return filas > 0


class DjangoVariableRepositorio(VariableRepositorio):

    @staticmethod
    def _a_entidad(m: VariableModel) -> Variable:
        return Variable(
            id=m.id,
            base_conocimiento_id=m.base_conocimiento_id,
            nombre=m.nombre,
            tipo_dato=TipoDato(m.tipo_dato),
            valor_defecto=m.valor_defecto,
            pregunta=m.pregunta,
            es_inicial=m.es_inicial,
            descripcion=m.descripcion,
        )

    def obtener_por_id(self, id_variable: UUID) -> Optional[Variable]:
        try:
            return self._a_entidad(VariableModel.objects.get(id=id_variable))
        except VariableModel.DoesNotExist:
            return None

    def listar_por_base(self, id_base: UUID) -> List[Variable]:
        qs = VariableModel.objects.filter(base_conocimiento_id=id_base).order_by("nombre")
        return [self._a_entidad(m) for m in qs]

    def existe_nombre_en_base(
        self, id_base: UUID, nombre: str, excluir_id: Optional[UUID] = None
    ) -> bool:
        qs = VariableModel.objects.filter(base_conocimiento_id=id_base, nombre__iexact=nombre)
        if excluir_id:
            qs = qs.exclude(id=excluir_id)
        return qs.exists()

    def guardar(self, variable: Variable) -> Variable:
        m, _ = VariableModel.objects.update_or_create(
            id=variable.id,
            defaults={
                "base_conocimiento_id": variable.base_conocimiento_id,
                "nombre": variable.nombre,
                "tipo_dato": (
                    variable.tipo_dato.value
                    if hasattr(variable.tipo_dato, "value")
                    else variable.tipo_dato
                ),
                "valor_defecto": variable.valor_defecto,
                "pregunta": variable.pregunta,
                "es_inicial": variable.es_inicial,
                "descripcion": variable.descripcion,
            },
        )
        return self._a_entidad(m)

    def eliminar(self, id_variable: UUID) -> bool:
        filas, _ = VariableModel.objects.filter(id=id_variable).delete()
        return filas > 0


class DjangoCondicionRepositorio(CondicionRepositorio):

    @staticmethod
    def _a_entidad(m: CondicionModel) -> Condicion:
        return Condicion(
            id=m.id,
            regla_id=m.regla_id,
            variable_id=m.variable_id,
            hecho_id=m.hecho_id,
            operador=OperadorCondicion(m.operador),
            valor_esperado=m.valor_esperado,
            orden=m.orden,
        )

    def obtener_por_id(self, id_condicion: UUID) -> Optional[Condicion]:
        try:
            return self._a_entidad(CondicionModel.objects.get(id=id_condicion))
        except CondicionModel.DoesNotExist:
            return None

    def listar_por_regla(self, id_regla: UUID) -> List[Condicion]:
        return [
            self._a_entidad(m)
            for m in CondicionModel.objects.filter(regla_id=id_regla).order_by("orden")
        ]

    def guardar(self, condicion: Condicion) -> Condicion:
        m, _ = CondicionModel.objects.update_or_create(
            id=condicion.id,
            defaults={
                "regla_id": condicion.regla_id,
                "variable_id": condicion.variable_id,
                "hecho_id": condicion.hecho_id,
                "operador": (
                    condicion.operador.value
                    if hasattr(condicion.operador, "value")
                    else condicion.operador
                ),
                "valor_esperado": condicion.valor_esperado,
                "orden": condicion.orden,
            },
        )
        return self._a_entidad(m)

    def eliminar(self, id_condicion: UUID) -> bool:
        filas, _ = CondicionModel.objects.filter(id=id_condicion).delete()
        return filas > 0


class DjangoConclusionRepositorio(ConclusionRepositorio):

    @staticmethod
    def _a_entidad(m: ConclusionModel) -> Conclusion:
        return Conclusion(
            id=m.id,
            regla_id=m.regla_id,
            hecho_resultante_id=m.hecho_resultante_id,
            variable_resultante_id=m.variable_resultante_id,
            valor_resultante=m.valor_resultante,
        )

    def obtener_por_id(self, id_conclusion: UUID) -> Optional[Conclusion]:
        try:
            return self._a_entidad(ConclusionModel.objects.get(id=id_conclusion))
        except ConclusionModel.DoesNotExist:
            return None

    def listar_por_regla(self, id_regla: UUID) -> List[Conclusion]:
        return [
            self._a_entidad(m) for m in ConclusionModel.objects.filter(regla_id=id_regla)
        ]

    def guardar(self, conclusion: Conclusion) -> Conclusion:
        m, _ = ConclusionModel.objects.update_or_create(
            id=conclusion.id,
            defaults={
                "regla_id": conclusion.regla_id,
                "hecho_resultante_id": conclusion.hecho_resultante_id,
                "variable_resultante_id": conclusion.variable_resultante_id,
                "valor_resultante": conclusion.valor_resultante,
            },
        )
        return self._a_entidad(m)

    def eliminar(self, id_conclusion: UUID) -> bool:
        filas, _ = ConclusionModel.objects.filter(id=id_conclusion).delete()
        return filas > 0


class DjangoReglaRepositorio(ReglaRepositorio):

    def _a_entidad(self, m: ReglaModel) -> Regla:
        condiciones = [
            DjangoCondicionRepositorio._a_entidad(c) for c in m.condiciones.all()
        ]
        conclusiones = [
            DjangoConclusionRepositorio._a_entidad(c) for c in m.conclusiones.all()
        ]
        return Regla(
            id=m.id,
            base_conocimiento_id=m.base_conocimiento_id,
            nombre=m.nombre,
            descripcion=m.descripcion,
            prioridad=m.prioridad,
            factor_certeza=m.factor_certeza,
            activa=m.activa,
            condiciones=condiciones,
            conclusiones=conclusiones,
        )

    def obtener_por_id(self, id_regla: UUID) -> Optional[Regla]:
        try:
            m = ReglaModel.objects.prefetch_related("condiciones", "conclusiones").get(
                id=id_regla
            )
            return self._a_entidad(m)
        except ReglaModel.DoesNotExist:
            return None

    def listar_por_base(self, id_base: UUID) -> List[Regla]:
        modelos = (
            ReglaModel.objects.filter(base_conocimiento_id=id_base)
            .prefetch_related("condiciones", "conclusiones")
            .order_by("-prioridad", "nombre")
        )
        return [self._a_entidad(m) for m in modelos]

    def listar_activas_por_base(self, id_base: UUID) -> List[Regla]:
        modelos = (
            ReglaModel.objects.filter(base_conocimiento_id=id_base, activa=True)
            .prefetch_related("condiciones", "conclusiones")
            .order_by("-prioridad", "id")
        )
        return [self._a_entidad(m) for m in modelos]

    def existe_nombre_en_base(
        self, id_base: UUID, nombre: str, excluir_id: Optional[UUID] = None
    ) -> bool:
        qs = ReglaModel.objects.filter(base_conocimiento_id=id_base, nombre__iexact=nombre)
        if excluir_id:
            qs = qs.exclude(id=excluir_id)
        return qs.exists()

    def guardar(self, regla: Regla) -> Regla:
        m, _ = ReglaModel.objects.update_or_create(
            id=regla.id,
            defaults={
                "base_conocimiento_id": regla.base_conocimiento_id,
                "nombre": regla.nombre,
                "descripcion": regla.descripcion,
                "prioridad": regla.prioridad,
                "factor_certeza": regla.factor_certeza,
                "activa": regla.activa,
            },
        )
        return self._a_entidad(m)

    def eliminar(self, id_regla: UUID) -> bool:
        filas, _ = ReglaModel.objects.filter(id=id_regla).delete()
        return filas > 0
