"""
Servicios y casos de uso para el módulo de Base de Conocimiento.
"""
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from apps.base_conocimiento.entities import (
    BaseConocimiento,
    Conclusion,
    Condicion,
    Hecho,
    Regla,
    Variable,
)
from apps.base_conocimiento.exceptions import (
    BaseConocimientoNoEncontrada,
    ConclusionNoEncontrada,
    CondicionNoEncontrada,
    HechoDuplicadoError,
    HechoNoEncontrado,
    ReglaDuplicadaError,
    ReglaNoEncontrada,
    VariableDuplicadaError,
    VariableNoEncontrada,
)
from apps.base_conocimiento.repositories import (
    BaseConocimientoRepositorio,
    ConclusionRepositorio,
    CondicionRepositorio,
    DjangoBaseConocimientoRepositorio,
    DjangoConclusionRepositorio,
    DjangoCondicionRepositorio,
    DjangoHechoRepositorio,
    DjangoReglaRepositorio,
    DjangoVariableRepositorio,
    HechoRepositorio,
    ReglaRepositorio,
    VariableRepositorio,
)
from apps.base_conocimiento.validators import ValidadorBaseConocimiento
from compartido.constantes.enums import OperadorCondicion, TipoDato
from compartido.excepciones.base import ExcepcionValidacionDominio

VALOR_NO_ENVIADO = object()


def _valor_inicial_opcional(valor):
    return None if valor is None or (isinstance(valor, str) and not valor.strip()) else valor


# =====================================================================
# SERVICIOS DE DOMINIO
# =====================================================================

class ServicioDominioRegla:
    """Reglas de negocio relativas a las reglas de producción."""

    @staticmethod
    def validar_regla_para_inferencia(regla: Regla) -> None:
        """Verifica que una regla activa cuente con al menos una condición y una conclusión."""
        if not regla.condiciones:
            raise ExcepcionValidacionDominio(
                f"La regla '{regla.nombre}' no tiene condiciones asociadas.",
                {"condiciones": ["Una regla activa requiere al menos una condición."]},
            )
        if not regla.conclusiones:
            raise ExcepcionValidacionDominio(
                f"La regla '{regla.nombre}' no tiene conclusiones asociadas.",
                {"conclusiones": ["Una regla activa requiere al menos una conclusión."]},
            )


# =====================================================================
# CASOS DE USO: BASE DE CONOCIMIENTO
# =====================================================================

class ObtenerBaseConocimiento:
    def __init__(self, repo_bc: Optional[BaseConocimientoRepositorio] = None):
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()

    def ejecutar_por_sistema(self, id_sistema: UUID) -> BaseConocimiento:
        bc = self.repo_bc.obtener_por_sistema_experto_id(id_sistema)
        if not bc:
            raise BaseConocimientoNoEncontrada(id_sistema)
        return bc

    def ejecutar_por_id(self, id_base: UUID) -> BaseConocimiento:
        bc = self.repo_bc.obtener_por_id(id_base)
        if not bc:
            raise BaseConocimientoNoEncontrada(id_base)
        return bc


# =====================================================================
# CASOS DE USO: HECHOS
# =====================================================================

class CrearHecho:
    def __init__(
        self,
        repo_hecho: Optional[HechoRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
    ):
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()

    def ejecutar(
        self,
        base_conocimiento_id: UUID,
        nombre: str,
        valor: Optional[str] = None,
        tipo_dato: str = TipoDato.TEXTO.value,
        opciones: Optional[List[str]] = None,
        pregunta: Optional[str] = None,
        es_inicial: bool = True,
    ) -> Hecho:
        nombre = nombre.strip()
        ValidadorBaseConocimiento.validar_tipo_dato(tipo_dato)

        if not self.repo_bc.obtener_por_id(base_conocimiento_id):
            raise BaseConocimientoNoEncontrada(base_conocimiento_id)

        if self.repo_hecho.existe_nombre_en_base(base_conocimiento_id, nombre):
            raise HechoDuplicadoError(nombre)

        hecho = Hecho(
            base_conocimiento_id=base_conocimiento_id,
            nombre=nombre,
            valor=_valor_inicial_opcional(valor),
            tipo_dato=TipoDato(tipo_dato),
            opciones=opciones or [],
            pregunta=pregunta if es_inicial else None,
            es_inicial=es_inicial,
        )
        return self.repo_hecho.guardar(hecho)


class ActualizarHecho:
    def __init__(self, repo_hecho: Optional[HechoRepositorio] = None):
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()

    def ejecutar(
        self,
        id_hecho: UUID,
        nombre: Optional[str] = None,
        valor: Any = VALOR_NO_ENVIADO,
        tipo_dato: Optional[str] = None,
        opciones: Optional[List[str]] = None,
        pregunta: Optional[str] = None,
        es_inicial: Optional[bool] = None,
    ) -> Hecho:
        hecho = self.repo_hecho.obtener_por_id(id_hecho)
        if not hecho:
            raise HechoNoEncontrado(id_hecho)

        if nombre is not None:
            nombre = nombre.strip()
            if self.repo_hecho.existe_nombre_en_base(
                hecho.base_conocimiento_id, nombre, excluir_id=id_hecho
            ):
                raise HechoDuplicadoError(nombre)
            hecho.nombre = nombre

        if valor is not VALOR_NO_ENVIADO:
            hecho.valor = _valor_inicial_opcional(valor)

        if tipo_dato is not None:
            ValidadorBaseConocimiento.validar_tipo_dato(tipo_dato)
            hecho.tipo_dato = TipoDato(tipo_dato)

        if opciones is not None:
            hecho.opciones = opciones

        if es_inicial is not None:
            hecho.es_inicial = es_inicial

        if not hecho.es_inicial:
            hecho.pregunta = None
        elif pregunta is not None:
            hecho.pregunta = pregunta

        return self.repo_hecho.guardar(hecho)


class ObtenerHecho:
    def __init__(self, repo_hecho: Optional[HechoRepositorio] = None):
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()

    def ejecutar(self, id_hecho: UUID) -> Hecho:
        hecho = self.repo_hecho.obtener_por_id(id_hecho)
        if not hecho:
            raise HechoNoEncontrado(id_hecho)
        return hecho


class ListarHechos:
    def __init__(self, repo_hecho: Optional[HechoRepositorio] = None):
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()

    def ejecutar(self, base_conocimiento_id: UUID) -> List[Hecho]:
        return self.repo_hecho.listar_por_base(base_conocimiento_id)


class EliminarHecho:
    def __init__(self, repo_hecho: Optional[HechoRepositorio] = None):
        self.repo_hecho = repo_hecho or DjangoHechoRepositorio()

    def ejecutar(self, id_hecho: UUID) -> None:
        hecho = self.repo_hecho.obtener_por_id(id_hecho)
        if not hecho:
            raise HechoNoEncontrado(id_hecho)
        self.repo_hecho.eliminar(id_hecho)


# =====================================================================
# CASOS DE USO: VARIABLES
# =====================================================================

class CrearVariable:
    def __init__(
        self,
        repo_variable: Optional[VariableRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
    ):
        self.repo_variable = repo_variable or DjangoVariableRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()

    def ejecutar(
        self,
        base_conocimiento_id: UUID,
        nombre: str,
        tipo_dato: str = TipoDato.TEXTO.value,
        valor_defecto: Optional[str] = None,
        pregunta: Optional[str] = None,
        es_inicial: bool = False,
        descripcion: Optional[str] = None,
    ) -> Variable:
        nombre = nombre.strip()
        ValidadorBaseConocimiento.validar_tipo_dato(tipo_dato)

        if not self.repo_bc.obtener_por_id(base_conocimiento_id):
            raise BaseConocimientoNoEncontrada(base_conocimiento_id)

        if self.repo_variable.existe_nombre_en_base(base_conocimiento_id, nombre):
            raise VariableDuplicadaError(nombre)

        variable = Variable(
            base_conocimiento_id=base_conocimiento_id,
            nombre=nombre,
            tipo_dato=TipoDato(tipo_dato),
            valor_defecto=_valor_inicial_opcional(valor_defecto),
            pregunta=pregunta if es_inicial else None,
            es_inicial=es_inicial,
            descripcion=descripcion,
        )
        return self.repo_variable.guardar(variable)


class ActualizarVariable:
    def __init__(self, repo_variable: Optional[VariableRepositorio] = None):
        self.repo_variable = repo_variable or DjangoVariableRepositorio()

    def ejecutar(
        self,
        id_variable: UUID,
        nombre: Optional[str] = None,
        tipo_dato: Optional[str] = None,
        valor_defecto: Any = VALOR_NO_ENVIADO,
        pregunta: Optional[str] = None,
        es_inicial: Optional[bool] = None,
        descripcion: Optional[str] = None,
    ) -> Variable:
        variable = self.repo_variable.obtener_por_id(id_variable)
        if not variable:
            raise VariableNoEncontrada(id_variable)

        if nombre is not None:
            nombre = nombre.strip()
            if self.repo_variable.existe_nombre_en_base(
                variable.base_conocimiento_id, nombre, excluir_id=id_variable
            ):
                raise VariableDuplicadaError(nombre)
            variable.nombre = nombre

        if tipo_dato is not None:
            ValidadorBaseConocimiento.validar_tipo_dato(tipo_dato)
            variable.tipo_dato = TipoDato(tipo_dato)

        if valor_defecto is not VALOR_NO_ENVIADO:
            variable.valor_defecto = _valor_inicial_opcional(valor_defecto)

        if es_inicial is not None:
            variable.es_inicial = es_inicial

        if not variable.es_inicial:
            variable.pregunta = None
        elif pregunta is not None:
            variable.pregunta = pregunta

        if descripcion is not None:
            variable.descripcion = descripcion

        return self.repo_variable.guardar(variable)


class ObtenerVariable:
    def __init__(self, repo_variable: Optional[VariableRepositorio] = None):
        self.repo_variable = repo_variable or DjangoVariableRepositorio()

    def ejecutar(self, id_variable: UUID) -> Variable:
        variable = self.repo_variable.obtener_por_id(id_variable)
        if not variable:
            raise VariableNoEncontrada(id_variable)
        return variable


class ListarVariables:
    def __init__(self, repo_variable: Optional[VariableRepositorio] = None):
        self.repo_variable = repo_variable or DjangoVariableRepositorio()

    def ejecutar(self, base_conocimiento_id: UUID) -> List[Variable]:
        return self.repo_variable.listar_por_base(base_conocimiento_id)


class EliminarVariable:
    def __init__(self, repo_variable: Optional[VariableRepositorio] = None):
        self.repo_variable = repo_variable or DjangoVariableRepositorio()

    def ejecutar(self, id_variable: UUID) -> None:
        variable = self.repo_variable.obtener_por_id(id_variable)
        if not variable:
            raise VariableNoEncontrada(id_variable)
        self.repo_variable.eliminar(id_variable)


# =====================================================================
# CASOS DE USO: REGLAS
# =====================================================================

class CrearRegla:
    def __init__(
        self,
        repo_regla: Optional[ReglaRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
    ):
        self.repo_regla = repo_regla or DjangoReglaRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()

    def ejecutar(
        self,
        base_conocimiento_id: UUID,
        nombre: str,
        descripcion: Optional[str] = None,
        prioridad: int = 0,
        factor_certeza: Optional[Decimal] = None,
        activa: bool = True,
    ) -> Regla:
        nombre = nombre.strip()
        ValidadorBaseConocimiento.validar_prioridad(prioridad)
        ValidadorBaseConocimiento.validar_factor_certeza(factor_certeza)

        if not self.repo_bc.obtener_por_id(base_conocimiento_id):
            raise BaseConocimientoNoEncontrada(base_conocimiento_id)

        if self.repo_regla.existe_nombre_en_base(base_conocimiento_id, nombre):
            raise ReglaDuplicadaError(nombre)

        regla = Regla(
            base_conocimiento_id=base_conocimiento_id,
            nombre=nombre,
            descripcion=descripcion,
            prioridad=prioridad,
            factor_certeza=factor_certeza,
            activa=activa,
        )
        return self.repo_regla.guardar(regla)


class ActualizarRegla:
    def __init__(self, repo_regla: Optional[ReglaRepositorio] = None):
        self.repo_regla = repo_regla or DjangoReglaRepositorio()

    def ejecutar(
        self,
        id_regla: UUID,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        prioridad: Optional[int] = None,
        factor_certeza: Optional[Decimal] = None,
        activa: Optional[bool] = None,
    ) -> Regla:
        regla = self.repo_regla.obtener_por_id(id_regla)
        if not regla:
            raise ReglaNoEncontrada(id_regla)

        if nombre is not None:
            nombre = nombre.strip()
            if self.repo_regla.existe_nombre_en_base(
                regla.base_conocimiento_id, nombre, excluir_id=id_regla
            ):
                raise ReglaDuplicadaError(nombre)
            regla.nombre = nombre

        if descripcion is not None:
            regla.descripcion = descripcion

        if prioridad is not None:
            ValidadorBaseConocimiento.validar_prioridad(prioridad)
            regla.prioridad = prioridad

        if factor_certeza is not None:
            ValidadorBaseConocimiento.validar_factor_certeza(factor_certeza)
            regla.factor_certeza = factor_certeza

        if activa is not None:
            regla.activa = activa

        return self.repo_regla.guardar(regla)


class ObtenerRegla:
    def __init__(self, repo_regla: Optional[ReglaRepositorio] = None):
        self.repo_regla = repo_regla or DjangoReglaRepositorio()

    def ejecutar(self, id_regla: UUID) -> Regla:
        regla = self.repo_regla.obtener_por_id(id_regla)
        if not regla:
            raise ReglaNoEncontrada(id_regla)
        return regla


class ListarReglas:
    def __init__(self, repo_regla: Optional[ReglaRepositorio] = None):
        self.repo_regla = repo_regla or DjangoReglaRepositorio()

    def ejecutar(self, base_conocimiento_id: UUID) -> List[Regla]:
        return self.repo_regla.listar_por_base(base_conocimiento_id)


class EliminarRegla:
    def __init__(self, repo_regla: Optional[ReglaRepositorio] = None):
        self.repo_regla = repo_regla or DjangoReglaRepositorio()

    def ejecutar(self, id_regla: UUID) -> None:
        regla = self.repo_regla.obtener_por_id(id_regla)
        if not regla:
            raise ReglaNoEncontrada(id_regla)
        self.repo_regla.eliminar(id_regla)


# =====================================================================
# CASOS DE USO: CONDICIONES
# =====================================================================

class AgregarCondicionARegla:
    def __init__(
        self,
        repo_cond: Optional[CondicionRepositorio] = None,
        repo_regla: Optional[ReglaRepositorio] = None,
    ):
        self.repo_cond = repo_cond or DjangoCondicionRepositorio()
        self.repo_regla = repo_regla or DjangoReglaRepositorio()

    def ejecutar(
        self,
        regla_id: UUID,
        operador: str,
        valor_esperado: str,
        variable_id: Optional[UUID] = None,
        hecho_id: Optional[UUID] = None,
        orden: int = 1,
    ) -> Condicion:
        ValidadorBaseConocimiento.validar_referencia_condicion(variable_id, hecho_id)

        if not self.repo_regla.obtener_por_id(regla_id):
            raise ReglaNoEncontrada(regla_id)

        condicion = Condicion(
            regla_id=regla_id,
            variable_id=variable_id,
            hecho_id=hecho_id,
            operador=OperadorCondicion(operador),
            valor_esperado=valor_esperado,
            orden=orden,
        )
        return self.repo_cond.guardar(condicion)


class ActualizarCondicion:
    def __init__(self, repo_cond: Optional[CondicionRepositorio] = None):
        self.repo_cond = repo_cond or DjangoCondicionRepositorio()

    def ejecutar(
        self,
        id_condicion: UUID,
        operador: Optional[str] = None,
        valor_esperado: Optional[str] = None,
        variable_id: Optional[UUID] = None,
        hecho_id: Optional[UUID] = None,
        orden: Optional[int] = None,
    ) -> Condicion:
        cond = self.repo_cond.obtener_por_id(id_condicion)
        if not cond:
            raise CondicionNoEncontrada(id_condicion)

        # Si se envían referencias, validar exclusividad
        if variable_id is not None or hecho_id is not None:
            v_id = variable_id if variable_id is not None else cond.variable_id
            h_id = hecho_id if hecho_id is not None else cond.hecho_id
            ValidadorBaseConocimiento.validar_referencia_condicion(v_id, h_id)
            cond.variable_id = variable_id
            cond.hecho_id = hecho_id

        if operador is not None:
            cond.operador = OperadorCondicion(operador)

        if valor_esperado is not None:
            cond.valor_esperado = valor_esperado

        if orden is not None:
            cond.orden = orden

        return self.repo_cond.guardar(cond)


class EliminarCondicion:
    def __init__(self, repo_cond: Optional[CondicionRepositorio] = None):
        self.repo_cond = repo_cond or DjangoCondicionRepositorio()

    def ejecutar(self, id_condicion: UUID) -> None:
        cond = self.repo_cond.obtener_por_id(id_condicion)
        if not cond:
            raise CondicionNoEncontrada(id_condicion)
        self.repo_cond.eliminar(id_condicion)


# =====================================================================
# CASOS DE USO: CONCLUSIONES
# =====================================================================

class AgregarConclusionARegla:
    def __init__(
        self,
        repo_conc: Optional[ConclusionRepositorio] = None,
        repo_regla: Optional[ReglaRepositorio] = None,
    ):
        self.repo_conc = repo_conc or DjangoConclusionRepositorio()
        self.repo_regla = repo_regla or DjangoReglaRepositorio()

    def ejecutar(
        self,
        regla_id: UUID,
        valor_resultante: str,
        hecho_resultante_id: Optional[UUID] = None,
        variable_resultante_id: Optional[UUID] = None,
    ) -> Conclusion:
        ValidadorBaseConocimiento.validar_destino_conclusion(
            hecho_resultante_id, variable_resultante_id
        )

        if not self.repo_regla.obtener_por_id(regla_id):
            raise ReglaNoEncontrada(regla_id)

        conclusion = Conclusion(
            regla_id=regla_id,
            hecho_resultante_id=hecho_resultante_id,
            variable_resultante_id=variable_resultante_id,
            valor_resultante=valor_resultante,
        )
        return self.repo_conc.guardar(conclusion)


class ActualizarConclusion:
    def __init__(self, repo_conc: Optional[ConclusionRepositorio] = None):
        self.repo_conc = repo_conc or DjangoConclusionRepositorio()

    def ejecutar(
        self,
        id_conclusion: UUID,
        valor_resultante: Optional[str] = None,
        hecho_resultante_id: Optional[UUID] = None,
        variable_resultante_id: Optional[UUID] = None,
    ) -> Conclusion:
        conc = self.repo_conc.obtener_por_id(id_conclusion)
        if not conc:
            raise ConclusionNoEncontrada(id_conclusion)

        if hecho_resultante_id is not None or variable_resultante_id is not None:
            h_id = hecho_resultante_id if hecho_resultante_id is not None else conc.hecho_resultante_id
            v_id = variable_resultante_id if variable_resultante_id is not None else conc.variable_resultante_id
            ValidadorBaseConocimiento.validar_destino_conclusion(h_id, v_id)
            conc.hecho_resultante_id = hecho_resultante_id
            conc.variable_resultante_id = variable_resultante_id

        if valor_resultante is not None:
            conc.valor_resultante = valor_resultante

        return self.repo_conc.guardar(conc)


class EliminarConclusion:
    def __init__(self, repo_conc: Optional[ConclusionRepositorio] = None):
        self.repo_conc = repo_conc or DjangoConclusionRepositorio()

    def ejecutar(self, id_conclusion: UUID) -> None:
        conc = self.repo_conc.obtener_por_id(id_conclusion)
        if not conc:
            raise ConclusionNoEncontrada(id_conclusion)
        self.repo_conc.eliminar(id_conclusion)
