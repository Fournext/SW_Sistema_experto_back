"""
Módulo de Explicabilidad Determinista Simbólica (Sprint 2 - HU-17).
Genera el árbol causal y la justificación estructurada de la conclusión final
a partir de la traza real de ejecución, sin depender de LLMs.
"""
from typing import Any, Dict, List, Optional, Set
from uuid import UUID
from types import SimpleNamespace


class MotorExplicabilidad:
    """
    Construye explicaciones deterministas a partir de los hechos y reglas ejecutadas.
    Aplica encadenamiento hacia atrás sobre la traza histórica.
    """

    @classmethod
    def construir_explicacion(
        cls,
        conclusion_final: Optional[str],
        hechos_iniciales: List[Dict[str, Any]],
        pasos: List[Any],
        nombres: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Reconstruye el árbol de justificación determinista de la conclusión.
        """
        if not conclusion_final:
            return {
                "conclusion": None,
                "texto": "No se alcanzó ninguna conclusión final durante el razonamiento.",
                "arbol": {
                    "tipo": "VACIO",
                    "mensaje": "La memoria de trabajo no produjo deducciones finales.",
                },
                "reglas_involucradas": [],
                "hechos_clave": [],
            }

        # 1. Identificar reglas disparadas y hechos generados por cada regla
        reglas_ejecutadas: List[Dict[str, Any]] = []
        mapa_hecho_a_regla: Dict[str, Dict[str, Any]] = {}
        conjunto_hechos_iniciales = {h.get("nombre") for h in hechos_iniciales}

        for paso in pasos:
            # paso puede ser un PasoInferencia, PasoEjecucionResultado o dict
            regla = getattr(paso, "regla_disparada", None)
            regla_id = getattr(paso, "regla_disparada_id", None) or getattr(regla, "id", None)
            regla_nombre = getattr(paso, "regla_nombre", None) or getattr(regla, "nombre", "Regla")
            condiciones_list = []
            if regla and hasattr(regla, "condiciones"):
                for c in regla.condiciones or []:
                    referencia = getattr(c, "hecho_id", None) or getattr(c, "variable_id", None)
                    sujeto = (nombres or {}).get(str(referencia), "Condición")
                    operador = getattr(c, "operador", "=")
                    esperado = getattr(c, "valor_esperado", "")
                    condiciones_list.append(f"{sujeto} {operador} {esperado}")

            hechos_gen = getattr(paso, "hechos_generados", [])
            info_regla = {
                "numero_paso": getattr(paso, "numero_paso", 1),
                "regla_id": str(regla_id) if regla_id else None,
                "regla_nombre": regla_nombre,
                "condiciones": condiciones_list,
                "hechos_generados": hechos_gen,
                "descripcion": getattr(paso, "descripcion", ""),
            }

            if regla_id:
                reglas_ejecutadas.append(info_regla)
                for hg in hechos_gen:
                    nombre_h = hg.get("nombre") if isinstance(hg, dict) else getattr(hg, "nombre", None)
                    if nombre_h:
                        mapa_hecho_a_regla[nombre_h] = info_regla

        # 2. Construir nodos del árbol causal
        nodos_arbol = []
        lineas_texto = [
            f"### Justificación Determinista de la Conclusión: `{conclusion_final}`\n",
            "La conclusión se obtuvo a través de la siguiente cadena causal demostrada:\n",
        ]

        orden = 1
        hechos_clave: Set[str] = set()
        reglas_clave: List[str] = []

        for r_info in reglas_ejecutadas:
            reglas_clave.append(r_info["regla_nombre"])
            hechos_str = ", ".join(
                f"{h.get('nombre')} = {h.get('valor')}" if isinstance(h, dict) else str(h)
                for h in r_info["hechos_generados"]
            )
            for h in r_info["hechos_generados"]:
                if isinstance(h, dict) and "nombre" in h:
                    hechos_clave.add(h["nombre"])

            lineas_texto.append(
                f"{orden}. **Paso {r_info['numero_paso']}**: Se disparó la regla **{r_info['regla_nombre']}**."
            )
            if r_info["descripcion"]:
                lineas_texto.append(f"   - *Detalle:* {r_info['descripcion']}")
            if hechos_str:
                lineas_texto.append(f"   - *Hechos deducidos:* `{hechos_str}`")

            nodos_arbol.append(
                {
                    "paso": r_info["numero_paso"],
                    "regla": r_info["regla_nombre"],
                    "regla_id": r_info["regla_id"],
                    "hechos_resultantes": r_info["hechos_generados"],
                }
            )
            orden += 1

        lineas_texto.append(
            f"\n**Resultado Final:** Memoria de trabajo consolidada con la conclusión `{conclusion_final}`."
        )

        return {
            "conclusion": conclusion_final,
            "texto": "\n".join(lineas_texto),
            "arbol": {
                "tipo": "CADENA_CAUSAL",
                "conclusion": conclusion_final,
                "nodos": nodos_arbol,
                "hechos_iniciales": list(conjunto_hechos_iniciales),
            },
            "reglas_involucradas": reglas_clave,
            "hechos_clave": list(hechos_clave),
        }

    @classmethod
    def construir_explicacion_detallada(
        cls, conclusion_final, hechos_iniciales, pasos, reglas, nombres,
        hechos_generados, detalles, explicacion_legacy=None,
    ):
        """Reconstruye la explicación de corridas existentes desde su registro real.

        Los valores y disparos provienen del histórico; las etiquetas y el factor
        configurado se resuelven desde las definiciones disponibles de las reglas.
        No se atribuye una certeza global que el motor no haya calculado.
        """
        reglas_por_id = {str(r.id): r for r in reglas}
        iniciales_por_nombre = {h["nombre"]: h for h in hechos_iniciales if h.get("nombre")}
        generados_por_paso = {}
        for hecho in hechos_generados:
            generados_por_paso.setdefault(str(hecho.paso_id), []).append(hecho)

        disparos = []
        cadena = []
        relevantes = set()
        producidos = set()
        pasos_completos = []
        deducciones = []
        for paso in pasos:
            regla_id = str(paso.regla_disparada_id) if paso.regla_disparada_id else None
            if not regla_id:
                continue
            regla = reglas_por_id.get(regla_id)
            nombre_regla = getattr(regla, "nombre", None) or paso.regla_nombre or "Regla eliminada"
            registros = [d for d in detalles if str(d.regla_id) == regla_id and d.paso_numero == paso.numero_paso]
            traza = next((d for d in reversed(registros) if str(d.estado_regla) == "EJECUTADA"), None)
            resultados = {str(c["condicion_id"]): c["resultado"] for d in registros for c in d.condiciones_evaluadas}
            condiciones = []
            for condicion in getattr(regla, "condiciones", []):
                # Las trazas modernas permiten omitir premisas que no pertenecían a esta evaluación.
                if resultados and resultados.get(str(condicion.id)) is not True:
                    continue
                referencia = condicion.hecho_id or condicion.variable_id
                nombre = nombres.get(str(referencia), "Dato no disponible")
                operador = getattr(condicion.operador, "value", condicion.operador)
                condiciones.append(f"{nombre} {operador} {condicion.valor_esperado}")
                if nombre in iniciales_por_nombre and nombre not in producidos:
                    relevantes.add(nombre)

            generados = generados_por_paso.get(str(paso.id), [])
            salidas = [{"nombre": h.nombre, "valor": h.valor} for h in generados]
            # Registros antiguos pueden tener el cambio en la BH aunque no tengan filas de hechos derivados.
            if not salidas:
                salidas = [{"nombre": nombre, "valor": valor} for nombre, valor in paso.memoria_trabajo_post.items()
                           if nombre not in paso.memoria_trabajo_pre or paso.memoria_trabajo_pre[nombre] != valor]
            consecuencia = ", ".join(f"{h['nombre']} = {h['valor']}" for h in salidas)
            if not consecuencia and traza:
                consecuencia = traza.resultado_generado or ""
            if not consecuencia:
                consecuencia = "Sin cambios en la memoria de trabajo."
            numero = getattr(traza, "paso_visual", None) or paso.numero_paso
            deducciones.extend({**h, "paso": numero} for h in salidas)
            producidos.update(h["nombre"] for h in salidas)
            factor = getattr(regla, "factor_certeza", None)
            disparos.append({
                "id": regla_id, "nombre": nombre_regla,
                "prioridad": getattr(regla, "prioridad", None),
                "factor_certeza": float(factor) if factor is not None else None,
                "condiciones_cumplidas": condiciones,
                "consecuencia": consecuencia,
            })
            premisas = " Y ".join(condiciones) or "Premisas no disponibles en el registro."
            cadena.append(f"Paso {numero}: {nombre_regla}. SI {premisas} ENTONCES {consecuencia}")
            pasos_completos.append(SimpleNamespace(
                numero_paso=numero, regla_disparada_id=paso.regla_disparada_id,
                regla_nombre=nombre_regla, regla_disparada=regla,
                hechos_generados=salidas, descripcion=cadena[-1],
            ))

        legacy = cls.construir_explicacion(conclusion_final, hechos_iniciales, pasos_completos, nombres)
        if not pasos_completos and explicacion_legacy:
            legacy.update(explicacion_legacy)
        indice_final = next((i for i in range(len(deducciones) - 1, -1, -1)
                             if str(deducciones[i]["valor"]) == str(conclusion_final)), None)
        nombre_final = deducciones[indice_final]["nombre"] if indice_final is not None else None
        if conclusion_final is None:
            resumen = "No se alcanzó ninguna conclusión final durante esta ejecución."
        else:
            resultado = f"{nombre_final} = {conclusion_final}" if nombre_final else str(conclusion_final)
            resumen = f"Se obtuvo {resultado} tras disparar {len(disparos)} regla(s)."
        return {
            **legacy,
            "conclusion_nombre": nombre_final,
            "conclusion_valor": conclusion_final,
            "factor_certeza_final": None,
            "hechos_iniciales_relevantes": [{"nombre": h["nombre"], "valor": h.get("valor")}
                                            for h in hechos_iniciales if h.get("nombre") in relevantes],
            "hechos_intermedios_derivados": [h for i, h in enumerate(deducciones) if i != indice_final],
            "reglas_disparadas": disparos,
            "cadena_razonamiento": cadena,
            "resumen_explicativo": resumen,
        }
