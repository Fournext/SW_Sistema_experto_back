"""
Motor de Validación Analítico e Independiente de Bases de Conocimiento (Sprint 2 - HU-18, HU-19).
Evalúa consistencia lógica, integridad referencial, estructura de grafos y tipos de datos.
Completamente desacoplado de Django y del motor de inferencia.
"""
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from apps.base_conocimiento.entities import Hecho, Regla, Variable
from apps.validacion.entities import IncidenciaValidacion, ResultadoValidacion
from compartido.constantes.enums import OperadorCondicion, SeveridadIncidencia, TipoDato, TipoIncidencia


class MotorValidacion:
    """Motor analítico determinista para inspección estática de bases de conocimiento."""

    @classmethod
    def validar(
        cls,
        base_conocimiento_id: UUID,
        hechos: List[Hecho],
        variables: List[Variable],
        reglas: List[Regla],
    ) -> ResultadoValidacion:
        incidencias: List[IncidenciaValidacion] = []

        mapa_hechos: Dict[UUID, Hecho] = {h.id: h for h in hechos}
        mapa_variables: Dict[UUID, Variable] = {v.id: v for v in variables}
        nombres_hechos = {h.nombre for h in hechos}
        nombres_variables = {v.nombre for v in variables}

        hechos_producidos: Set[UUID] = set()
        variables_producidas: Set[UUID] = set()
        variables_leidas: Set[UUID] = set()
        hechos_leidos: Set[UUID] = set()

        # -------------------------------------------------------------
        # 1. Validación de Reglas Individuales: Condiciones y Conclusiones
        # -------------------------------------------------------------
        for r in reglas:
            if not r.activa:
                continue

            # VAL-004: Reglas sin condiciones
            if not r.condiciones:
                incidencias.append(
                    IncidenciaValidacion(
                        codigo="VAL-004",
                        tipo=TipoIncidencia.ESTRUCTURAL.value,
                        severidad=SeveridadIncidencia.ERROR.value,
                        entidad_tipo="REGLA",
                        entidad_id=r.id,
                        entidad_nombre=r.nombre,
                        descripcion=f"La regla '{r.nombre}' no tiene ninguna condición configurada.",
                        posible_causa="La regla fue creada pero no se le añadieron antecedentes.",
                        sugerencia="Agregue al menos una condición a la regla en el editor.",
                    )
                )

            # VAL-005: Reglas sin conclusiones
            if not r.conclusiones:
                incidencias.append(
                    IncidenciaValidacion(
                        codigo="VAL-005",
                        tipo=TipoIncidencia.ESTRUCTURAL.value,
                        severidad=SeveridadIncidencia.ERROR.value,
                        entidad_tipo="REGLA",
                        entidad_id=r.id,
                        entidad_nombre=r.nombre,
                        descripcion=f"La regla '{r.nombre}' no tiene ninguna conclusión configurada.",
                        posible_causa="La regla carece de consecuentes o acciones a disparar.",
                        sugerencia="Defina al menos una conclusión resultante para la regla.",
                    )
                )

            # Revisión de condiciones
            for c in r.condiciones or []:
                target_id = c.hecho_id or c.variable_id
                # VAL-003: Referencias inexistentes en condiciones
                if c.hecho_id and c.hecho_id not in mapa_hechos:
                    incidencias.append(
                        IncidenciaValidacion(
                            codigo="VAL-003",
                            tipo=TipoIncidencia.REFERENCIAL.value,
                            severidad=SeveridadIncidencia.ERROR.value,
                            entidad_tipo="CONDICION",
                            entidad_id=c.id,
                            entidad_nombre=f"Condición de {r.nombre}",
                            descripcion=f"La condición hace referencia a un hecho inexistente ({c.hecho_id}).",
                            posible_causa="El hecho fue eliminado de la base sin actualizar la regla.",
                            sugerencia="Reasigne la condición a un hecho o variable válido.",
                        )
                    )
                elif c.variable_id and c.variable_id not in mapa_variables:
                    incidencias.append(
                        IncidenciaValidacion(
                            codigo="VAL-003",
                            tipo=TipoIncidencia.REFERENCIAL.value,
                            severidad=SeveridadIncidencia.ERROR.value,
                            entidad_tipo="CONDICION",
                            entidad_id=c.id,
                            entidad_nombre=f"Condición de {r.nombre}",
                            descripcion=f"La condición hace referencia a una variable inexistente ({c.variable_id}).",
                            posible_causa="La variable fue eliminada sin actualizar la regla.",
                            sugerencia="Reasigne la condición a una variable existente.",
                        )
                    )

                if c.hecho_id and c.hecho_id in mapa_hechos:
                    hechos_leidos.add(c.hecho_id)
                    tipo_d = mapa_hechos[c.hecho_id].tipo_dato
                    cls._validar_compatibilidad_tipo(c, tipo_d, r, incidencias)

                if c.variable_id and c.variable_id in mapa_variables:
                    variables_leidas.add(c.variable_id)
                    tipo_d = mapa_variables[c.variable_id].tipo_dato
                    cls._validar_compatibilidad_tipo(c, tipo_d, r, incidencias)

            # Revisión de conclusiones
            for conc in r.conclusiones or []:
                if conc.hecho_resultante_id:
                    if conc.hecho_resultante_id not in mapa_hechos:
                        incidencias.append(
                            IncidenciaValidacion(
                                codigo="VAL-003",
                                tipo=TipoIncidencia.REFERENCIAL.value,
                                severidad=SeveridadIncidencia.ERROR.value,
                                entidad_tipo="CONCLUSION",
                                entidad_id=conc.id,
                                entidad_nombre=f"Conclusión de {r.nombre}",
                                descripcion="La conclusión apunta a un hecho resultante inexistente.",
                                posible_causa="El hecho de destino fue eliminado.",
                                sugerencia="Corrija el destino de la conclusión.",
                            )
                        )
                    else:
                        hechos_producidos.add(conc.hecho_resultante_id)

                if conc.variable_resultante_id:
                    if conc.variable_resultante_id not in mapa_variables:
                        incidencias.append(
                            IncidenciaValidacion(
                                codigo="VAL-003",
                                tipo=TipoIncidencia.REFERENCIAL.value,
                                severidad=SeveridadIncidencia.ERROR.value,
                                entidad_tipo="CONCLUSION",
                                entidad_id=conc.id,
                                entidad_nombre=f"Conclusión de {r.nombre}",
                                descripcion="La conclusión apunta a una variable resultante inexistente.",
                                posible_causa="La variable destino fue eliminada.",
                                sugerencia="Corrija el destino de la conclusión.",
                            )
                        )
                    else:
                        variables_producidas.add(conc.variable_resultante_id)

        # -------------------------------------------------------------
        # 2. Detección de Reglas Duplicadas y Contradictorias (VAL-001, VAL-002)
        # -------------------------------------------------------------
        reglas_activas = [r for r in reglas if r.activa and r.condiciones and r.conclusiones]
        for i in range(len(reglas_activas)):
            r1 = reglas_activas[i]
            firma_cond_r1 = cls._firma_condiciones(r1)

            for j in range(i + 1, len(reglas_activas)):
                r2 = reglas_activas[j]
                firma_cond_r2 = cls._firma_condiciones(r2)

                # Si tienen exactamente las mismas condiciones
                if firma_cond_r1 == firma_cond_r2 and firma_cond_r1:
                    firma_conc_r1 = cls._firma_conclusiones(r1)
                    firma_conc_r2 = cls._firma_conclusiones(r2)

                    if firma_conc_r1 == firma_conc_r2:
                        # VAL-001: Reglas duplicadas
                        incidencias.append(
                            IncidenciaValidacion(
                                codigo="VAL-001",
                                tipo=TipoIncidencia.SEMANTICA.value,
                                severidad=SeveridadIncidencia.ADVERTENCIA.value,
                                entidad_tipo="REGLA",
                                entidad_id=r2.id,
                                entidad_nombre=r2.nombre,
                                descripcion=(
                                    f"La regla '{r2.nombre}' es un duplicado exacto de '{r1.nombre}' "
                                    f"(mismas condiciones y conclusiones)."
                                ),
                                posible_causa="Redundancia accidental al definir reglas.",
                                sugerencia="Desactive o elimine una de las reglas duplicadas.",
                            )
                        )
                    else:
                        # VAL-002: Reglas contradictorias (mismas condiciones pero conclusiones distintas)
                        # Comprobar si apuntan a los mismos destinos con valores diferentes
                        destinos_r1 = {c.variable_resultante_id or c.hecho_resultante_id: c.valor_resultante for c in r1.conclusiones}
                        destinos_r2 = {c.variable_resultante_id or c.hecho_resultante_id: c.valor_resultante for c in r2.conclusiones}

                        conflictos_dest = set(destinos_r1.keys()).intersection(destinos_r2.keys())
                        for dest in conflictos_dest:
                            if dest and destinos_r1[dest] != destinos_r2[dest]:
                                incidencias.append(
                                    IncidenciaValidacion(
                                        codigo="VAL-002",
                                        tipo=TipoIncidencia.SEMANTICA.value,
                                        severidad=SeveridadIncidencia.ERROR.value,
                                        entidad_tipo="REGLA",
                                        entidad_id=r2.id,
                                        entidad_nombre=r2.nombre,
                                        descripcion=(
                                            f"Regla potencialmente contradictoria con '{r1.nombre}': "
                                            f"ante idénticas condiciones, una asigna '{destinos_r1[dest]}' "
                                            f"y la otra '{destinos_r2[dest]}'."
                                        ),
                                        posible_causa="Inconsistencia semántica en la base de conocimiento.",
                                        sugerencia="Revise las condiciones o diferencie los antecedentes para evitar ambigüedad.",
                                    )
                                )

        # -------------------------------------------------------------
        # 3. Variables no utilizadas (VAL-006)
        # -------------------------------------------------------------
        for v in variables:
            if v.id not in variables_leidas and v.id not in variables_producidas:
                incidencias.append(
                    IncidenciaValidacion(
                        codigo="VAL-006",
                        tipo=TipoIncidencia.ESTRUCTURAL.value,
                        severidad=SeveridadIncidencia.ADVERTENCIA.value,
                        entidad_tipo="VARIABLE",
                        entidad_id=v.id,
                        entidad_nombre=v.nombre,
                        descripcion=f"La variable '{v.nombre}' no se evalúa en ninguna regla ni se asigna en ninguna conclusión.",
                        posible_causa="Variable declarada pero abandonada o sin reglas asociadas.",
                        sugerencia="Elimine la variable o incorpórela en las condiciones de las reglas.",
                    )
                )

        # -------------------------------------------------------------
        # 4. Condiciones inalcanzables (VAL-007)
        # -------------------------------------------------------------
        # Una entrada inicial puede obtener su valor durante la consulta.
        # No necesita un valor preasignado ni una regla que la produzca.
        hechos_iniciales_ids = {h.id for h in hechos if getattr(h, "es_inicial", True)}
        for r in reglas_activas:
            for c in r.condiciones or []:
                if c.hecho_id:
                    # Solo falta una fuente si no es inicial ni lo produce una regla activa.
                    if c.hecho_id not in hechos_iniciales_ids and c.hecho_id not in hechos_producidos:
                        h_obj = mapa_hechos.get(c.hecho_id)
                        nom = h_obj.nombre if h_obj else str(c.hecho_id)
                        incidencias.append(
                            IncidenciaValidacion(
                                codigo="VAL-007",
                                tipo=TipoIncidencia.SEMANTICA.value,
                                severidad=SeveridadIncidencia.ADVERTENCIA.value,
                                entidad_tipo="CONDICION",
                                entidad_id=c.id,
                                entidad_nombre=f"Condición sobre '{nom}' en {r.nombre}",
                                descripcion=(
                                    f"La condición depende del hecho '{nom}', el cual no está marcado como inicial "
                                    f"ni es generado por ninguna regla activa en la base."
                                ),
                                posible_causa="El hecho no tiene una fuente de entrada o deducción configurada.",
                                sugerencia="Marque el hecho como inicial si lo proporcionará el usuario o cree una regla activa que lo deduzca.",
                            )
                        )

        # -------------------------------------------------------------
        # 5. Dependencias Circulares Directas (VAL-010)
        # -------------------------------------------------------------
        for i in range(len(reglas_activas)):
            r1 = reglas_activas[i]
            r1_conclusiones = {c.hecho_resultante_id or c.variable_resultante_id for c in r1.conclusiones}
            r1_condiciones = {c.hecho_id or c.variable_id for c in r1.condiciones}

            for j in range(i + 1, len(reglas_activas)):
                r2 = reglas_activas[j]
                r2_conclusiones = {c.hecho_resultante_id or c.variable_resultante_id for c in r2.conclusiones}
                r2_condiciones = {c.hecho_id or c.variable_id for c in r2.condiciones}

                # Si r1 produce algo que r2 necesita y r2 produce algo que r1 necesita
                if (r1_conclusiones.intersection(r2_condiciones)) and (r2_conclusiones.intersection(r1_condiciones)):
                    incidencias.append(
                        IncidenciaValidacion(
                            codigo="VAL-010",
                            tipo=TipoIncidencia.CICLO.value,
                            severidad=SeveridadIncidencia.ADVERTENCIA.value,
                            entidad_tipo="REGLA",
                            entidad_id=r2.id,
                            entidad_nombre=f"{r1.nombre} <-> {r2.nombre}",
                            descripcion=(
                                f"Dependencia circular potencial detectada entre las reglas '{r1.nombre}' y '{r2.nombre}'."
                            ),
                            posible_causa="Ciclo mutuo de antecedentes y consecuentes entre dos reglas.",
                            sugerencia="Revise si el ciclo es intencional o si puede derivar en iteraciones innecesarias.",
                        )
                    )

        # Consolidación de resultado
        total_err = sum(1 for inc in incidencias if inc.severidad == SeveridadIncidencia.ERROR.value)
        total_adv = sum(1 for inc in incidencias if inc.severidad == SeveridadIncidencia.ADVERTENCIA.value)
        es_valida = (total_err == 0)

        resumen = (
            f"Validación finalizada con éxito: Base de Conocimiento consistente y válida."
            if es_valida and total_adv == 0
            else f"Validación finalizada: {total_err} error(es) bloqueante(s) y {total_adv} advertencia(s) potencial(es)."
        )

        return ResultadoValidacion(
            base_conocimiento_id=base_conocimiento_id,
            es_valida=es_valida,
            total_errores=total_err,
            total_advertencias=total_adv,
            resumen=resumen,
            incidencias=incidencias,
        )

    @classmethod
    def _validar_compatibilidad_tipo(
        cls, condicion: Any, tipo_dato: Any, regla: Regla, incidencias: List[IncidenciaValidacion]
    ):
        """VAL-008 y VAL-009: Valida que el operador y valor coincidan con el tipo de dato."""
        tipo_str = str(tipo_dato.value if hasattr(tipo_dato, "value") else tipo_dato).upper()
        op = str(condicion.operador)
        val = str(condicion.valor_esperado).strip()

        if tipo_str == "BOOLEANO":
            if op not in ("=", "!="):
                incidencias.append(
                    IncidenciaValidacion(
                        codigo="VAL-008",
                        tipo=TipoIncidencia.ESTRUCTURAL.value,
                        severidad=SeveridadIncidencia.ERROR.value,
                        entidad_tipo="CONDICION",
                        entidad_id=condicion.id,
                        entidad_nombre=f"Condición en {regla.nombre}",
                        descripcion=f"Operador '{op}' no válido para tipo BOOLEANO (solo se admiten '=' y '!=').",
                        posible_causa="Configuración errónea de operador relacional.",
                        sugerencia="Cambie el operador a '=' o '!='.",
                    )
                )
            if val.lower() not in ("true", "false", "1", "0", "si", "no"):
                incidencias.append(
                    IncidenciaValidacion(
                        codigo="VAL-009",
                        tipo=TipoIncidencia.ESTRUCTURAL.value,
                        severidad=SeveridadIncidencia.ERROR.value,
                        entidad_tipo="CONDICION",
                        entidad_id=condicion.id,
                        entidad_nombre=f"Condición en {regla.nombre}",
                        descripcion=f"El valor '{val}' no es un booleano válido.",
                        posible_causa="Texto arbitrario en campo booleano.",
                        sugerencia="Establezca 'true' o 'false'.",
                    )
                )

        elif tipo_str in ("ENTERO", "DECIMAL"):
            try:
                float(val)
            except ValueError:
                incidencias.append(
                    IncidenciaValidacion(
                        codigo="VAL-009",
                        tipo=TipoIncidencia.ESTRUCTURAL.value,
                        severidad=SeveridadIncidencia.ERROR.value,
                        entidad_tipo="CONDICION",
                        entidad_id=condicion.id,
                        entidad_nombre=f"Condición en {regla.nombre}",
                        descripcion=f"El valor '{val}' no es un número válido para el tipo {tipo_str}.",
                        posible_causa="Caracteres no numéricos en valor esperado numérico.",
                        sugerencia="Ingrese un valor numérico válido.",
                    )
                )

    @staticmethod
    def _firma_condiciones(r: Regla) -> frozenset:
        firmas = []
        for c in r.condiciones or []:
            sujeto = str(c.hecho_id or c.variable_id or "")
            firmas.append((sujeto, str(c.operador), str(c.valor_esperado).strip().lower()))
        return frozenset(firmas)

    @staticmethod
    def _firma_conclusiones(r: Regla) -> frozenset:
        firmas = []
        for c in r.conclusiones or []:
            dest = str(c.hecho_resultante_id or c.variable_resultante_id or "")
            firmas.append((dest, str(c.valor_resultante).strip().lower()))
        return frozenset(firmas)
