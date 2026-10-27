"""Estado del recorrido de reglas, independiente de los pasos de conflicto."""
import copy


def nuevo_recorrido(memoria, numero_vuelta=1, progreso_visual=None):
    progreso_visual = progreso_visual or {}
    return {
        "numero_vuelta": numero_vuelta,
        "visitadas": [],
        "memoria_inicio": copy.deepcopy(memoria),
        "hubo_disparo": False,
        "contador_visual": progreso_visual.get("contador_visual", 0),
        "paso_visual_actual": progreso_visual.get("paso_visual_actual", 0),
        "grupo_pequeno": None,
    }


def ordenar_reglas(reglas):
    return sorted(reglas, key=lambda r: (-r.prioridad, r.nombre, str(r.id)))


def pendientes_recorrido(reglas, ejecutadas, recorrido):
    omitidas = {str(id_regla) for id_regla in ejecutadas} | set(recorrido.get("visitadas", []))
    return [r for r in ordenar_reglas(reglas) if str(r.id) not in omitidas]


def cerrar_vuelta(recorrido, memoria, reglas, ejecutadas):
    """Devuelve (estado, finalizado), sin volver a ejecutar reglas disparadas."""
    if pendientes_recorrido(reglas, ejecutadas, recorrido):
        return recorrido, False
    pendientes = pendientes_recorrido(reglas, ejecutadas, {})
    if pendientes and recorrido.get("hubo_disparo") and memoria != recorrido.get("memoria_inicio", {}):
        return nuevo_recorrido(memoria, recorrido.get("numero_vuelta", 1) + 1, recorrido), False
    recorrido["grupo_pequeno"] = None
    return recorrido, True


def asignar_paso_visual(recorrido, es_recorrido, paso_fisico_anterior):
    # Un historial anterior a este metadato conserva su numeración física.
    # La primera agrupación nueva debe quedar después, nunca colisionar con él.
    contador = recorrido.get("contador_visual", paso_fisico_anterior)
    grupo = recorrido.get("grupo_pequeno") if es_recorrido else None
    if grupo is None:
        contador += 1
        grupo = contador
        recorrido["contador_visual"] = contador
        if es_recorrido:
            recorrido["grupo_pequeno"] = grupo
    recorrido["paso_visual_actual"] = grupo
    return grupo
