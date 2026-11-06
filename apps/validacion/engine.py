"""
Motor de Validación Analítico e Independiente de Bases de Conocimiento (Sprint 2 - HU-18, HU-19).
Evalúa consistencia lógica, integridad referencial, estructura de grafos y tipos de datos.
Completamente desacoplado de Django y del motor de inferencia.
"""
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from apps.base_conocimiento.entities import Conclusion, Condicion, Hecho, Regla, Variable
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

        # -------------------------------------------------------------
        # 6. Contradicciones entre Hechos Iniciales (VAL-011)
        # -------------------------------------------------------------
        cls._analizar_hechos_contradictorios(hechos, incidencias)

        # -------------------------------------------------------------
        # 7. Condiciones Lógicamente Imposibles (VAL-015)
        # -------------------------------------------------------------
        cls._analizar_condiciones_imposibles(
            reglas_activas, mapa_hechos, mapa_variables, incidencias
        )

        # -------------------------------------------------------------
        # 8. Contradicciones Directas por Satisfacibilidad (VAL-012)
        # -------------------------------------------------------------
        cls._analizar_contradicciones_por_satisfacibilidad(
            reglas_activas, mapa_hechos, mapa_variables, incidencias
        )

        # -------------------------------------------------------------
        # 9. Contradicciones Indirectas en Cadenas de Inferencia (VAL-013)
        # -------------------------------------------------------------
        cls._analizar_contradicciones_indirectas(
            hechos, variables, reglas_activas, mapa_hechos, mapa_variables, incidencias
        )

        # -------------------------------------------------------------
        # 10. Contradicción Hecho Inicial vs Regla (VAL-014)
        # -------------------------------------------------------------
        cls._analizar_contradicciones_hecho_regla(
            hechos, reglas_activas, mapa_hechos, incidencias
        )

        # -------------------------------------------------------------
        # 11. Hechos Iniciales sin Fuente de Entrada (VAL-016)
        # -------------------------------------------------------------
        # Hechos iniciales sin valor se capturan en consulta

        # -------------------------------------------------------------
        # 12. Valores Fuera de Dominio en Tipo OPCION (VAL-017)
        # -------------------------------------------------------------
        cls._analizar_valores_fuera_de_dominio(
            reglas_activas, mapa_hechos, mapa_variables, incidencias
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

    # =========================================================================
    # ANALIZADORES AVANZADOS (VAL-011 a VAL-017)
    # =========================================================================

    @staticmethod
    def _normalizar_booleano(val: Any) -> Optional[bool]:
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if s in ("true", "1", "si", "sí", "verdadero"):
            return True
        if s in ("false", "0", "no", "falso"):
            return False
        return None

    @classmethod
    def _analizar_hechos_contradictorios(
        cls, hechos: List[Hecho], incidencias: List[IncidenciaValidacion]
    ):
        """VAL-011: Detecta hechos iniciales con el mismo nombre y valores mutuamente incompatibles."""
        por_nombre: Dict[str, List[Hecho]] = {}
        for h in hechos:
            if getattr(h, "es_inicial", True):
                nom_norm = h.nombre.strip().lower()
                por_nombre.setdefault(nom_norm, []).append(h)

        for nom, grupo in por_nombre.items():
            if len(grupo) < 2:
                continue

            valores_vistos = []
            for h in grupo:
                if h.valor is not None and str(h.valor).strip():
                    bool_val = cls._normalizar_booleano(h.valor)
                    val_repr = str(bool_val).lower() if bool_val is not None else str(h.valor).strip().lower()
                    valores_vistos.append((val_repr, h))

            if len(valores_vistos) >= 2:
                primer_val, primer_h = valores_vistos[0]
                hay_conflicto = any(v != primer_val for v, _ in valores_vistos)
                if hay_conflicto:
                    valores_str = ", ".join(f"'{h.valor}'" for _, h in valores_vistos)
                    h_afectado = valores_vistos[-1][1]
                    incidencias.append(
                        IncidenciaValidacion(
                            codigo="VAL-011",
                            tipo=TipoIncidencia.LOGICO.value,
                            severidad=SeveridadIncidencia.ERROR.value,
                            entidad_tipo="HECHO",
                            entidad_id=h_afectado.id,
                            entidad_nombre=primer_h.nombre,
                            descripcion=(
                                f"Existen hechos iniciales contradictorios para '{primer_h.nombre}'. "
                                f"Se declararon valores incompatibles: {valores_str} simultáneamente."
                            ),
                            posible_causa="Valores iniciales opuestos o inconsistentes definidos para la misma entidad.",
                            sugerencia="Asegúrese de que cada hecho inicial tenga un único valor consistente.",
                        )
                    )

    @classmethod
    def _evaluar_satisfacibilidad_intervalo(cls, condiciones: List[Condicion]) -> Tuple[bool, str]:
        """
        Evalúa si un conjunto de condiciones numéricas sobre la misma entidad es satisfacible.
        Devuelve (es_satisfacible, detalle).
        """
        lower = float("-inf")
        upper = float("inf")
        lower_strict = False
        upper_strict = False
        puntos_excluidos: Set[float] = set()
        punto_exacto: Optional[float] = None

        for c in condiciones:
            try:
                val = float(str(c.valor_esperado).replace(",", "."))
            except (ValueError, TypeError):
                continue

            op = str(c.operador.value if hasattr(c.operador, "value") else c.operador)
            if op == ">":
                if val > lower or (val == lower and not lower_strict):
                    lower = val
                    lower_strict = True
            elif op == ">=":
                if val > lower:
                    lower = val
                    lower_strict = False
            elif op == "<":
                if val < upper or (val == upper and not upper_strict):
                    upper = val
                    upper_strict = True
            elif op == "<=":
                if val < upper:
                    upper = val
                    upper_strict = False
            elif op == "=":
                if punto_exacto is not None and punto_exacto != val:
                    return False, f"= {punto_exacto} y = {val}"
                punto_exacto = val
            elif op == "!=":
                puntos_excluidos.add(val)

        if punto_exacto is not None:
            if punto_exacto < lower or (punto_exacto == lower and lower_strict):
                return False, f"= {punto_exacto} con límite inferior > {lower}"
            if punto_exacto > upper or (punto_exacto == upper and upper_strict):
                return False, f"= {punto_exacto} con límite superior < {upper}"
            if punto_exacto in puntos_excluidos:
                return False, f"= {punto_exacto} y != {punto_exacto}"
            return True, f"= {punto_exacto}"

        if lower > upper:
            return False, f"> {lower} y < {upper}"
        if lower == upper:
            if lower_strict or upper_strict:
                return False, f"límite {lower} excluido por desigualdad estricta"
            if lower in puntos_excluidos:
                return False, f"= {lower} pero explícitamente excluido"

        return True, f"intervalo ({lower}, {upper})"

    @classmethod
    def _analizar_condiciones_imposibles(
        cls,
        reglas_activas: List[Regla],
        mapa_hechos: Dict[UUID, Hecho],
        mapa_variables: Dict[UUID, Variable],
        incidencias: List[IncidenciaValidacion],
    ):
        """VAL-015: Detecta reglas cuyas condiciones internas nunca pueden cumplirse simultáneamente."""
        for r in reglas_activas:
            por_sujeto: Dict[UUID, List[Condicion]] = {}
            for c in r.condiciones or []:
                sujeto_id = c.hecho_id or c.variable_id
                if sujeto_id:
                    por_sujeto.setdefault(sujeto_id, []).append(c)

            for sujeto_id, conds in por_sujeto.items():
                if len(conds) < 2:
                    continue

                obj = mapa_hechos.get(sujeto_id) or mapa_variables.get(sujeto_id)
                nom_sujeto = obj.nombre if obj else str(sujeto_id)
                tipo_str = str(getattr(obj, "tipo_dato", "")).upper()

                # Caso Numérico
                if "ENTERO" in tipo_str or "DECIMAL" in tipo_str:
                    satisfacible, detalle = cls._evaluar_satisfacibilidad_intervalo(conds)
                    if not satisfacible:
                        incidencias.append(
                            IncidenciaValidacion(
                                codigo="VAL-015",
                                tipo=TipoIncidencia.LOGICO.value,
                                severidad=SeveridadIncidencia.ERROR.value,
                                entidad_tipo="REGLA",
                                entidad_id=r.id,
                                entidad_nombre=r.nombre,
                                descripcion=(
                                    f"La regla '{r.nombre}' contiene condiciones mutuamente imposibles sobre '{nom_sujeto}' "
                                    f"({detalle}). Ningún valor numérico puede satisfacerlas a la vez."
                                ),
                                posible_causa="Rango numérico contradictorio o condiciones excluyentes en una misma regla.",
                                sugerencia="Ajuste los operadores y valores relacionales para que definan un rango alcanzable.",
                            )
                        )
                # Caso Booleano
                elif "BOOLEANO" in tipo_str:
                    valores_bool = set()
                    for c in conds:
                        b = cls._normalizar_booleano(c.valor_esperado)
                        op = str(c.operador.value if hasattr(c.operador, "value") else c.operador)
                        if op == "=" and b is not None:
                            valores_bool.add(b)
                    if len(valores_bool) > 1:
                        incidencias.append(
                            IncidenciaValidacion(
                                codigo="VAL-015",
                                tipo=TipoIncidencia.LOGICO.value,
                                severidad=SeveridadIncidencia.ERROR.value,
                                entidad_tipo="REGLA",
                                entidad_id=r.id,
                                entidad_nombre=r.nombre,
                                descripcion=(
                                    f"La regla '{r.nombre}' exige simultáneamente que '{nom_sujeto}' sea verdadero y falso."
                                ),
                                posible_causa="Condiciones booleanas contradictorias en el antecedente.",
                                sugerencia="Elimine la condición contradictoria.",
                            )
                        )
                # Caso Texto / Opcion con igualdad simultánea
                elif "TEXTO" in tipo_str or "OPCION" in tipo_str:
                    valores_igualdad = set()
                    for c in conds:
                        op = str(c.operador.value if hasattr(c.operador, "value") else c.operador)
                        if op == "=":
                            valores_igualdad.add(str(c.valor_esperado).strip().lower())
                    if len(valores_igualdad) > 1:
                        incidencias.append(
                            IncidenciaValidacion(
                                codigo="VAL-015",
                                tipo=TipoIncidencia.LOGICO.value,
                                severidad=SeveridadIncidencia.ERROR.value,
                                entidad_tipo="REGLA",
                                entidad_id=r.id,
                                entidad_nombre=r.nombre,
                                descripcion=(
                                    f"La regla '{r.nombre}' exige simultáneamente valores mutuamente excluyentes para '{nom_sujeto}' "
                                    f"({', '.join(valores_igualdad)})."
                                ),
                                posible_causa="Múltiples igualdades con valores distintos para una variable escalar.",
                                sugerencia="Revise las condiciones o utilice un operador disyuntivo si correspondiera.",
                            )
                        )

    @classmethod
    def _condiciones_son_compatibles(
        cls,
        conds_r1: List[Condicion],
        conds_r2: List[Condicion],
        mapa_hechos: Dict[UUID, Hecho],
        mapa_variables: Dict[UUID, Variable],
    ) -> bool:
        """Determina si dos conjuntos de condiciones son conjuntamente satisfacibles."""
        por_sujeto: Dict[UUID, List[Condicion]] = {}
        for c in (conds_r1 or []) + (conds_r2 or []):
            sujeto_id = c.hecho_id or c.variable_id
            if sujeto_id:
                por_sujeto.setdefault(sujeto_id, []).append(c)

        for sujeto_id, conds in por_sujeto.items():
            if len(conds) < 2:
                continue

            obj = mapa_hechos.get(sujeto_id) or mapa_variables.get(sujeto_id)
            tipo_str = str(getattr(obj, "tipo_dato", "")).upper()

            if "ENTERO" in tipo_str or "DECIMAL" in tipo_str:
                sat, _ = cls._evaluar_satisfacibilidad_intervalo(conds)
                if not sat:
                    return False
            elif "BOOLEANO" in tipo_str:
                bools = set()
                for c in conds:
                    b = cls._normalizar_booleano(c.valor_esperado)
                    op = str(c.operador.value if hasattr(c.operador, "value") else c.operador)
                    if op == "=" and b is not None:
                        bools.add(b)
                if len(bools) > 1:
                    return False
            else:
                igualdades = set()
                for c in conds:
                    op = str(c.operador.value if hasattr(c.operador, "value") else c.operador)
                    if op == "=":
                        igualdades.add(str(c.valor_esperado).strip().lower())
                if len(igualdades) > 1:
                    return False

        return True

    @classmethod
    def _analizar_contradicciones_por_satisfacibilidad(
        cls,
        reglas_activas: List[Regla],
        mapa_hechos: Dict[UUID, Hecho],
        mapa_variables: Dict[UUID, Variable],
        incidencias: List[IncidenciaValidacion],
    ):
        """VAL-012: Contradicciones directas entre reglas con condiciones compatibles no necesariamente idénticas."""
        for i in range(len(reglas_activas)):
            r1 = reglas_activas[i]
            for j in range(i + 1, len(reglas_activas)):
                r2 = reglas_activas[j]

                # Si las condiciones son idénticas, ya fueron reportadas en VAL-002
                if cls._firma_condiciones(r1) == cls._firma_condiciones(r2):
                    continue

                # Verificar si concluyen valores opuestos sobre el mismo destino
                destinos_r1 = {
                    (c.variable_resultante_id or c.hecho_resultante_id): c.valor_resultante
                    for c in (r1.conclusiones or [])
                    if c.valor_resultante is not None
                }
                destinos_r2 = {
                    (c.variable_resultante_id or c.hecho_resultante_id): c.valor_resultante
                    for c in (r2.conclusiones or [])
                    if c.valor_resultante is not None
                }

                destinos_comunes = set(destinos_r1.keys()) & set(destinos_r2.keys())
                destinos_conflictivos = {
                    d
                    for d in destinos_comunes
                    if d and str(destinos_r1[d]).strip().lower() != str(destinos_r2[d]).strip().lower()
                }

                if not destinos_conflictivos:
                    continue

                # Analizar si las condiciones de r1 y r2 pueden cumplirse simultáneamente
                if cls._condiciones_son_compatibles(
                    r1.condiciones, r2.condiciones, mapa_hechos, mapa_variables
                ):
                    for dest in destinos_conflictivos:
                        obj_dest = mapa_hechos.get(dest) or mapa_variables.get(dest)
                        nom_dest = obj_dest.nombre if obj_dest else str(dest)
                        incidencias.append(
                            IncidenciaValidacion(
                                codigo="VAL-012",
                                tipo=TipoIncidencia.LOGICO.value,
                                severidad=SeveridadIncidencia.ERROR.value,
                                entidad_tipo="REGLA",
                                entidad_id=r2.id,
                                entidad_nombre=f"{r1.nombre} vs {r2.nombre}",
                                descripcion=(
                                    f"Las reglas '{r1.nombre}' y '{r2.nombre}' pueden activarse simultáneamente "
                                    f"ante condiciones compatibles y asignan valores contradictorios a '{nom_dest}' "
                                    f"('{destinos_r1[dest]}' vs '{destinos_r2[dest]}')."
                                ),
                                posible_causa="Condiciones con regiones de activación superpuestas pero conclusiones opuestas.",
                                sugerencia="Diferencie los antecedentes o acote los intervalos para evitar ambigüedad en la inferencia.",
                            )
                        )

    @classmethod
    def _analizar_contradicciones_indirectas(
        cls,
        hechos: List[Hecho],
        variables: List[Variable],
        reglas_activas: List[Regla],
        mapa_hechos: Dict[UUID, Hecho],
        mapa_variables: Dict[UUID, Variable],
        incidencias: List[IncidenciaValidacion],
    ):
        """VAL-013: Detecta contradicciones indirectas derivadas a través de cadenas de inferencia."""
        if len(reglas_activas) > 60:
            return

        for r_prod in reglas_activas:
            for conc_prod in r_prod.conclusiones or []:
                prod_dest = conc_prod.hecho_resultante_id or conc_prod.variable_resultante_id
                if not prod_dest or conc_prod.valor_resultante is None:
                    continue
                prod_val = str(conc_prod.valor_resultante).strip().lower()

                # Buscar reglas consumidoras que se activen con este valor producido
                for r_cons in reglas_activas:
                    if r_cons.id == r_prod.id:
                        continue

                    cond_coincide = False
                    for cond in r_cons.condiciones or []:
                        c_sujeto = cond.hecho_id or cond.variable_id
                        op = str(cond.operador.value if hasattr(cond.operador, "value") else cond.operador)
                        c_val = str(cond.valor_esperado).strip().lower()
                        if c_sujeto == prod_dest and op == "=" and c_val == prod_val:
                            cond_coincide = True
                            break

                    if not cond_coincide:
                        continue

                    # Conclusiones finales de la cadena
                    for conc_cons in r_cons.conclusiones or []:
                        cons_dest = conc_cons.hecho_resultante_id or conc_cons.variable_resultante_id
                        if not cons_dest or conc_cons.valor_resultante is None:
                            continue
                        cons_val = str(conc_cons.valor_resultante).strip().lower()

                        # Buscar conflicto con otra regla activa
                        for r_conflicto in reglas_activas:
                            if r_conflicto.id in (r_prod.id, r_cons.id):
                                continue

                            for conc_conf in r_conflicto.conclusiones or []:
                                conf_dest = conc_conf.hecho_resultante_id or conc_conf.variable_resultante_id
                                if conf_dest == cons_dest and conc_conf.valor_resultante is not None:
                                    conf_val = str(conc_conf.valor_resultante).strip().lower()
                                    if conf_val != cons_val:
                                        # Verificar si r_prod y r_conflicto son compatibles
                                        if cls._condiciones_son_compatibles(
                                            r_prod.condiciones,
                                            r_conflicto.condiciones,
                                            mapa_hechos,
                                            mapa_variables,
                                        ):
                                            obj_dest = mapa_hechos.get(cons_dest) or mapa_variables.get(cons_dest)
                                            nom_dest = obj_dest.nombre if obj_dest else str(cons_dest)
                                            incidencias.append(
                                                IncidenciaValidacion(
                                                    codigo="VAL-013",
                                                    tipo=TipoIncidencia.LOGICO.value,
                                                    severidad=SeveridadIncidencia.ERROR.value,
                                                    entidad_tipo="REGLA",
                                                    entidad_id=r_conflicto.id,
                                                    entidad_nombre=f"Cadena {r_prod.nombre} -> {r_cons.nombre} vs {r_conflicto.nombre}",
                                                    descripcion=(
                                                        f"Existe una contradicción indirecta: la cadena ({r_prod.nombre} -> {r_cons.nombre}) "
                                                        f"deriva '{nom_dest}' = '{conc_cons.valor_resultante}', mientras que "
                                                        f"'{r_conflicto.nombre}' concluye '{nom_dest}' = '{conc_conf.valor_resultante}' "
                                                        f"bajo antecedentes compatibles."
                                                    ),
                                                    posible_causa="Ramas de inferencia divergentes que alcanzan conclusiones incompatibles sobre el mismo objetivo.",
                                                    sugerencia="Revise la consistencia global del árbol de inferencia y unifique los consecuentes.",
                                                )
                                            )

    @classmethod
    def _analizar_contradicciones_hecho_regla(
        cls,
        hechos: List[Hecho],
        reglas_activas: List[Regla],
        mapa_hechos: Dict[UUID, Hecho],
        incidencias: List[IncidenciaValidacion],
    ):
        """VAL-014: Detecta cuando una regla concluye un valor incompatible con un hecho inicial afirmado."""
        hechos_iniciales_con_valor = {
            h.id: h
            for h in hechos
            if getattr(h, "es_inicial", True) and h.valor is not None and str(h.valor).strip()
        }

        for r in reglas_activas:
            for conc in r.conclusiones or []:
                if conc.hecho_resultante_id and conc.hecho_resultante_id in hechos_iniciales_con_valor:
                    h_inicial = hechos_iniciales_con_valor[conc.hecho_resultante_id]
                    val_inicial_bool = cls._normalizar_booleano(h_inicial.valor)
                    val_conc_bool = cls._normalizar_booleano(conc.valor_resultante)

                    difieren = False
                    if val_inicial_bool is not None and val_conc_bool is not None:
                        difieren = val_inicial_bool != val_conc_bool
                    else:
                        difieren = (
                            str(conc.valor_resultante).strip().lower()
                            != str(h_inicial.valor).strip().lower()
                        )

                    if difieren:
                        incidencias.append(
                            IncidenciaValidacion(
                                codigo="VAL-014",
                                tipo=TipoIncidencia.LOGICO.value,
                                severidad=SeveridadIncidencia.ERROR.value,
                                entidad_tipo="REGLA",
                                entidad_id=r.id,
                                entidad_nombre=r.nombre,
                                descripcion=(
                                    f"La regla '{r.nombre}' concluye un valor '{conc.valor_resultante}' para el hecho "
                                    f"'{h_inicial.nombre}' que contradice directamente su valor inicial ('{h_inicial.valor}')."
                                ),
                                posible_causa="Incompatibilidad semántica entre el postulado inicial y el consecuente de la regla.",
                                sugerencia="Revise si el hecho inicial debe actualizarse o si la regla debe restringir sus condiciones.",
                            )
                        )

    @classmethod
    def _analizar_hechos_sin_fuente(
        cls, hechos: List[Hecho], incidencias: List[IncidenciaValidacion]
    ):
        """VAL-016: Detecta hechos iniciales sin valor inicial ni pregunta asociada."""
        for h in hechos:
            if getattr(h, "es_inicial", True):
                valor_vacio = h.valor is None or not str(h.valor).strip()
                pregunta_vacia = h.pregunta is None or not str(h.pregunta).strip()
                if valor_vacio and pregunta_vacia:
                    incidencias.append(
                        IncidenciaValidacion(
                            codigo="VAL-016",
                            tipo=TipoIncidencia.ESTRUCTURAL.value,
                            severidad=SeveridadIncidencia.ADVERTENCIA.value,
                            entidad_tipo="HECHO",
                            entidad_id=h.id,
                            entidad_nombre=h.nombre,
                            descripcion=(
                                f"El hecho inicial '{h.nombre}' no tiene valor inicial asignado ni una pregunta configurada "
                                f"para interactuar con el usuario."
                            ),
                            posible_causa="Hecho de entrada configurado de forma incompleta.",
                            sugerencia="Asigne un valor predeterminado o redacte una pregunta para capturar su valor.",
                        )
                    )

    @classmethod
    def _analizar_valores_fuera_de_dominio(
        cls,
        reglas_activas: List[Regla],
        mapa_hechos: Dict[UUID, Hecho],
        mapa_variables: Dict[UUID, Variable],
        incidencias: List[IncidenciaValidacion],
    ):
        """VAL-017: Detecta conclusiones que asignan valores fuera del dominio permitido en tipo OPCION."""
        for r in reglas_activas:
            for conc in r.conclusiones or []:
                destino = None
                if conc.hecho_resultante_id and conc.hecho_resultante_id in mapa_hechos:
                    destino = mapa_hechos[conc.hecho_resultante_id]
                elif conc.variable_resultante_id and conc.variable_resultante_id in mapa_variables:
                    destino = mapa_variables[conc.variable_resultante_id]

                if not destino:
                    continue

                tipo_str = str(getattr(destino, "tipo_dato", "")).upper()
                if "OPCION" in tipo_str:
                    opciones_permitidas = getattr(destino, "opciones", []) or []
                    if opciones_permitidas:
                        opciones_norm = [str(op).strip().lower() for op in opciones_permitidas]
                        val_res = str(conc.valor_resultante or "").strip().lower()
                        if val_res not in opciones_norm:
                            incidencias.append(
                                IncidenciaValidacion(
                                    codigo="VAL-017",
                                    tipo=TipoIncidencia.ESTRUCTURAL.value,
                                    severidad=SeveridadIncidencia.ERROR.value,
                                    entidad_tipo="CONCLUSION",
                                    entidad_id=conc.id,
                                    entidad_nombre=f"Conclusión en {r.nombre}",
                                    descripcion=(
                                        f"La regla '{r.nombre}' intenta asignar '{conc.valor_resultante}' al elemento '{destino.nombre}', "
                                        f"el cual no pertenece a sus opciones permitidas ({', '.join(opciones_permitidas)})."
                                    ),
                                    posible_causa="Valor resultante no listado en el dominio de la variable/hecho tipo OPCION.",
                                    sugerencia="Ajuste el valor resultante a una de las opciones predefinidas.",
                                )
                            )
