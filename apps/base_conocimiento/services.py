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


class CrearReglaCompleta:
    """
    Caso de uso transaccional para crear una Regla completa con sus Condiciones y Conclusiones.
    Resuelve o auto-crea variables y hechos si se proporcionan por nombre.
    """

    def __init__(
        self,
        repo_regla: Optional[ReglaRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
        repo_cond: Optional[CondicionRepositorio] = None,
        repo_conc: Optional[ConclusionRepositorio] = None,
        repo_var: Optional[VariableRepositorio] = None,
    ):
        self.repo_regla = repo_regla or DjangoReglaRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()
        self.repo_cond = repo_cond or DjangoCondicionRepositorio()
        self.repo_conc = repo_conc or DjangoConclusionRepositorio()
        self.repo_var = repo_var or DjangoVariableRepositorio()

    def ejecutar(
        self,
        base_conocimiento_id: UUID,
        nombre: str,
        prioridad: int = 10,
        descripcion: Optional[str] = None,
        factor_certeza: Optional[Decimal] = None,
        activa: bool = True,
        condiciones: Optional[List[dict]] = None,
        conclusiones: Optional[List[dict]] = None,
        posicion_x: Optional[float] = None,
        posicion_y: Optional[float] = None,
    ) -> Regla:
        from django.db import transaction
        from apps.base_conocimiento.models import (
            BaseConocimientoModel,
            HechoModel,
            VariableModel,
        )
        from apps.editor_visual.models import NodoVisualModel
        from compartido.constantes.enums import (
            OperadorCondicion,
            TipoDato,
            TipoNodoVisual,
        )

        nombre = nombre.strip()
        ValidadorBaseConocimiento.validar_prioridad(prioridad)
        ValidadorBaseConocimiento.validar_factor_certeza(factor_certeza)

        bc = self.repo_bc.obtener_por_id(base_conocimiento_id)
        if not bc:
            raise BaseConocimientoNoEncontrada(base_conocimiento_id)

        if self.repo_regla.existe_nombre_en_base(base_conocimiento_id, nombre):
            raise ReglaDuplicadaError(nombre)

        with transaction.atomic():
            # 1. Crear Regla
            regla_ent = Regla(
                base_conocimiento_id=base_conocimiento_id,
                nombre=nombre,
                descripcion=descripcion,
                prioridad=prioridad,
                factor_certeza=factor_certeza,
                activa=activa,
            )
            regla_guardada = self.repo_regla.guardar(regla_ent)

            # 2. Procesar Condiciones (Antecedentes IF)
            condiciones_list = condiciones or []
            for idx, c_data in enumerate(condiciones_list, start=1):
                operador = c_data.get("operador", "=")
                valor_esperado = str(c_data.get("valor_esperado", ""))
                v_id = c_data.get("variable_id")
                h_id = c_data.get("hecho_id")
                v_nombre = c_data.get("variable_nombre") or c_data.get("nombre")

                if not v_id and not h_id and v_nombre:
                    # Buscar variable o hecho existente
                    v_mod = VariableModel.objects.filter(
                        base_conocimiento_id=base_conocimiento_id,
                        nombre__iexact=v_nombre.strip(),
                    ).first()
                    if not v_mod:
                        h_mod = HechoModel.objects.filter(
                            base_conocimiento_id=base_conocimiento_id,
                            nombre__iexact=v_nombre.strip(),
                        ).first()
                        if h_mod:
                            h_id = h_mod.id
                        else:
                            # Auto-crear variable con su tipo de dato correspondiente (ENTERO, DECIMAL, TEXTO, BOOLEANO, OPCION)
                            raw_tipo = str(c_data.get("tipo_dato") or "").upper().strip()
                            if raw_tipo == "NUMERO":
                                tipo_dato_str = TipoDato.ENTERO.value
                            elif raw_tipo in [td.value for td in TipoDato]:
                                tipo_dato_str = raw_tipo
                            else:
                                tipo_dato_str = TipoDato.ENTERO.value
                            v_mod = VariableModel.objects.create(
                                base_conocimiento_id=base_conocimiento_id,
                                nombre=v_nombre.strip(),
                                tipo_dato=tipo_dato_str,
                            )
                            v_id = v_mod.id
                    else:
                        v_id = v_mod.id

                if not v_id and not h_id:
                    raise ValueError(f"La condición #{idx} debe especificar una variable o hecho.")

                cond_ent = Condicion(
                    regla_id=regla_guardada.id,
                    variable_id=UUID(str(v_id)) if v_id else None,
                    hecho_id=UUID(str(h_id)) if h_id else None,
                    operador=OperadorCondicion(operador),
                    valor_esperado=valor_esperado,
                    orden=c_data.get("orden", idx),
                )
                self.repo_cond.guardar(cond_ent)

            # 3. Procesar Conclusiones (Consecuentes THEN)
            conclusiones_list = conclusiones or []
            for idx, c_data in enumerate(conclusiones_list, start=1):
                valor_resultante = str(c_data.get("valor_resultante", ""))
                v_res_id = c_data.get("variable_resultante_id")
                h_res_id = c_data.get("hecho_resultante_id")
                v_nombre = c_data.get("variable_nombre") or c_data.get("destino")

                if not v_res_id and not h_res_id and v_nombre:
                    v_mod = VariableModel.objects.filter(
                        base_conocimiento_id=base_conocimiento_id,
                        nombre__iexact=v_nombre.strip(),
                    ).first()
                    if not v_mod:
                        h_mod = HechoModel.objects.filter(
                            base_conocimiento_id=base_conocimiento_id,
                            nombre__iexact=v_nombre.strip(),
                        ).first()
                        if h_mod:
                            h_res_id = h_mod.id
                        else:
                            raw_tipo_res = str(c_data.get("tipo_dato") or "").upper().strip()
                            if raw_tipo_res == "NUMERO":
                                tipo_dato_res = TipoDato.ENTERO.value
                            elif raw_tipo_res in [td.value for td in TipoDato]:
                                tipo_dato_res = raw_tipo_res
                            else:
                                tipo_dato_res = TipoDato.TEXTO.value
                            v_mod = VariableModel.objects.create(
                                base_conocimiento_id=base_conocimiento_id,
                                nombre=v_nombre.strip(),
                                tipo_dato=tipo_dato_res,
                            )
                            v_res_id = v_mod.id
                    else:
                        v_res_id = v_mod.id

                if not v_res_id and not h_res_id:
                    raise ValueError(f"La conclusión #{idx} debe especificar una variable o hecho resultante.")

                conc_ent = Conclusion(
                    regla_id=regla_guardada.id,
                    variable_resultante_id=UUID(str(v_res_id)) if v_res_id else None,
                    hecho_resultante_id=UUID(str(h_res_id)) if h_res_id else None,
                    valor_resultante=valor_resultante,
                )
                self.repo_conc.guardar(conc_ent)

            # 4. Crear Nodo Visual para la Regla con distribución automática en cuadrícula
            try:
                bc_model = BaseConocimientoModel.objects.select_related("sistema_experto").get(
                    id=base_conocimiento_id
                )
                if bc_model and bc_model.sistema_experto_id:
                    from apps.base_conocimiento.models import ReglaModel
                    count_reglas = max(0, ReglaModel.objects.filter(base_conocimiento_id=base_conocimiento_id).count() - 1)
                    grid_col = count_reglas % 3
                    grid_row = count_reglas // 3
                    auto_x = 60.0 + grid_col * 350.0
                    auto_y = 80.0 + grid_row * 320.0

                    x = posicion_x if posicion_x is not None else auto_x
                    y = posicion_y if posicion_y is not None else auto_y
                    NodoVisualModel.objects.update_or_create(
                        sistema_experto_id=bc_model.sistema_experto_id,
                        referencia_id=regla_guardada.id,
                        defaults={
                            "tipo": TipoNodoVisual.REGLA.value,
                            "posicion_x": x,
                            "posicion_y": y,
                        },
                    )
            except Exception:
                pass

        # Retornar la entidad completa con condiciones y conclusiones precargadas
        return self.repo_regla.obtener_por_id(regla_guardada.id)


class ActualizarReglaCompleta:
    """
    Caso de uso transaccional para actualizar una Regla y sincronizar
    sus Condiciones y Conclusiones (IF-THEN) de forma atómica.
    """

    def __init__(
        self,
        repo_regla: Optional[ReglaRepositorio] = None,
        repo_bc: Optional[BaseConocimientoRepositorio] = None,
        repo_cond: Optional[CondicionRepositorio] = None,
        repo_conc: Optional[ConclusionRepositorio] = None,
        repo_var: Optional[VariableRepositorio] = None,
    ):
        self.repo_regla = repo_regla or DjangoReglaRepositorio()
        self.repo_bc = repo_bc or DjangoBaseConocimientoRepositorio()
        self.repo_cond = repo_cond or DjangoCondicionRepositorio()
        self.repo_conc = repo_conc or DjangoConclusionRepositorio()
        self.repo_var = repo_var or DjangoVariableRepositorio()

    def ejecutar(
        self,
        id_regla: UUID,
        nombre: Optional[str] = None,
        prioridad: Optional[int] = None,
        descripcion: Optional[str] = None,
        factor_certeza: Optional[Decimal] = None,
        activa: Optional[bool] = None,
        condiciones: Optional[List[dict]] = None,
        conclusiones: Optional[List[dict]] = None,
    ) -> Regla:
        from django.db import transaction
        from apps.base_conocimiento.models import (
            CondicionModel,
            ConclusionModel,
            HechoModel,
            VariableModel,
        )
        from compartido.constantes.enums import OperadorCondicion, TipoDato

        regla = self.repo_regla.obtener_por_id(id_regla)
        if not regla:
            raise ReglaNoEncontrada(id_regla)

        base_conocimiento_id = regla.base_conocimiento_id

        with transaction.atomic():
            # 1. Actualizar campos de la Regla
            if nombre is not None:
                nombre = nombre.strip()
                if self.repo_regla.existe_nombre_en_base(
                    base_conocimiento_id, nombre, excluir_id=id_regla
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

            self.repo_regla.guardar(regla)

            # 2. Sincronizar Condiciones (SI / IF) si fueron provistas
            if condiciones is not None:
                CondicionModel.objects.filter(regla_id=id_regla).delete()
                for idx, c_data in enumerate(condiciones, start=1):
                    operador = c_data.get("operador", "=")
                    valor_esperado = str(c_data.get("valor_esperado", ""))
                    v_id = c_data.get("variable_id")
                    h_id = c_data.get("hecho_id")
                    v_nombre = c_data.get("variable_nombre") or c_data.get("nombre")

                    if not v_id and not h_id and v_nombre:
                        v_mod = VariableModel.objects.filter(
                            base_conocimiento_id=base_conocimiento_id,
                            nombre__iexact=v_nombre.strip(),
                        ).first()
                        if not v_mod:
                            h_mod = HechoModel.objects.filter(
                                base_conocimiento_id=base_conocimiento_id,
                                nombre__iexact=v_nombre.strip(),
                            ).first()
                            if h_mod:
                                h_id = h_mod.id
                            else:
                                raw_tipo = str(c_data.get("tipo_dato") or "").upper().strip()
                                if raw_tipo == "NUMERO":
                                    tipo_dato_str = TipoDato.ENTERO.value
                                elif raw_tipo in [td.value for td in TipoDato]:
                                    tipo_dato_str = raw_tipo
                                else:
                                    tipo_dato_str = TipoDato.ENTERO.value
                                v_mod = VariableModel.objects.create(
                                    base_conocimiento_id=base_conocimiento_id,
                                    nombre=v_nombre.strip(),
                                    tipo_dato=tipo_dato_str,
                                )
                                v_id = v_mod.id
                        else:
                            raw_tipo = str(c_data.get("tipo_dato") or "").upper().strip()
                            if raw_tipo in [td.value for td in TipoDato] and v_mod.tipo_dato != raw_tipo:
                                v_mod.tipo_dato = raw_tipo
                                v_mod.save(update_fields=["tipo_dato"])
                            v_id = v_mod.id

                    cond_ent = Condicion(
                        regla_id=id_regla,
                        variable_id=UUID(str(v_id)) if v_id else None,
                        hecho_id=UUID(str(h_id)) if h_id else None,
                        operador=OperadorCondicion(operador),
                        valor_esperado=valor_esperado,
                        orden=c_data.get("orden", idx),
                    )
                    self.repo_cond.guardar(cond_ent)

            # 3. Sincronizar Conclusiones (ENTONCES / THEN) si fueron provistas
            if conclusiones is not None:
                ConclusionModel.objects.filter(regla_id=id_regla).delete()
                for idx, c_data in enumerate(conclusiones, start=1):
                    valor_resultante = str(c_data.get("valor_resultante", ""))
                    v_res_id = c_data.get("variable_resultante_id")
                    h_res_id = c_data.get("hecho_resultante_id")
                    v_nombre = c_data.get("variable_nombre") or c_data.get("destino")

                    if not v_res_id and not h_res_id and v_nombre:
                        v_mod = VariableModel.objects.filter(
                            base_conocimiento_id=base_conocimiento_id,
                            nombre__iexact=v_nombre.strip(),
                        ).first()
                        if not v_mod:
                            h_mod = HechoModel.objects.filter(
                                base_conocimiento_id=base_conocimiento_id,
                                nombre__iexact=v_nombre.strip(),
                            ).first()
                            if h_mod:
                                h_res_id = h_mod.id
                            else:
                                raw_tipo_res = str(c_data.get("tipo_dato") or "").upper().strip()
                                if raw_tipo_res == "NUMERO":
                                    tipo_dato_res = TipoDato.ENTERO.value
                                elif raw_tipo_res in [td.value for td in TipoDato]:
                                    tipo_dato_res = raw_tipo_res
                                else:
                                    tipo_dato_res = TipoDato.TEXTO.value
                                v_mod = VariableModel.objects.create(
                                    base_conocimiento_id=base_conocimiento_id,
                                    nombre=v_nombre.strip(),
                                    tipo_dato=tipo_dato_res,
                                )
                                v_res_id = v_mod.id
                        else:
                            raw_tipo_res = str(c_data.get("tipo_dato") or "").upper().strip()
                            if raw_tipo_res in [td.value for td in TipoDato] and v_mod.tipo_dato != raw_tipo_res:
                                v_mod.tipo_dato = raw_tipo_res
                                v_mod.save(update_fields=["tipo_dato"])
                            v_res_id = v_mod.id

                    conc_ent = Conclusion(
                        regla_id=id_regla,
                        variable_resultante_id=UUID(str(v_res_id)) if v_res_id else None,
                        hecho_resultante_id=UUID(str(h_res_id)) if h_res_id else None,
                        valor_resultante=valor_resultante,
                    )
                    self.repo_conc.guardar(conc_ent)

        return self.repo_regla.obtener_por_id(id_regla)

