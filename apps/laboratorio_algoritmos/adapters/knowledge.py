"""
Adaptador de Base de Conocimiento para el Laboratorio de Algoritmos.
Extrae un snapshot inmutable y estructurado de la Base de Conocimiento
del sistema experto para alimentar la Máquina Virtual.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID
from apps.base_conocimiento.models import (
    BaseConocimientoModel,
    CondicionModel,
    ConclusionModel,
    HechoModel,
    ReglaModel,
    VariableModel,
)
from apps.laboratorio_algoritmos.runtime.values import (
    BaseHechosValue,
    HechoValor,
    ReglaRef,
    VariableRef,
)


def extraer_snapshot_base_conocimiento(
    sistema_experto_id: UUID | str,
    orden_reglas_ids: Optional[List[str]] = None,
    hechos_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Extrae la Base de Conocimiento completa asociada a un Sistema Experto
    en un formato serializable apto para el Laboratorio.
    """
    bc = BaseConocimientoModel.objects.filter(sistema_experto_id=sistema_experto_id).first()
    if not bc:
        raise ValueError(f"No existe Base de Conocimiento para el Sistema Experto {sistema_experto_id}")

    # Variables
    variables_qs = VariableModel.objects.filter(base_conocimiento=bc).order_by("nombre")
    variables = []
    for var in variables_qs:
        variables.append({
            "id": str(var.id),
            "nombre": var.nombre,
            "tipo_dato": var.tipo_dato,
            "valor_defecto": var.valor_defecto,
            "pregunta": var.pregunta,
            "es_inicial": var.es_inicial,
            "descripcion": var.descripcion or "",
        })

    # Hechos iniciales registrados en la base
    hechos_qs = HechoModel.objects.filter(base_conocimiento=bc)
    hechos_iniciales = []
    for h in hechos_qs:
        if h.es_inicial and h.valor is not None:
            hechos_iniciales.append({
                "variable": h.nombre,
                "valor": h.valor,
                "origen": "INICIAL",
            })

    # Si el usuario envió overrides de hechos iniciales
    if hechos_override:
        hechos_map = {h["variable"]: h for h in hechos_iniciales}
        for k, v in hechos_override.items():
            hechos_map[k] = {"variable": k, "valor": v, "origen": "USUARIO"}
        hechos_iniciales = list(hechos_map.values())

    # Reglas
    reglas_qs = ReglaModel.objects.filter(base_conocimiento=bc, activa=True).prefetch_related(
        "condiciones__variable", "condiciones__hecho",
        "conclusiones__variable_resultante", "conclusiones__hecho_resultante"
    )

    if orden_reglas_ids:
        reglas_por_id = {str(r.id): r for r in reglas_qs}
        reglas_ordenadas = [reglas_por_id[rid] for rid in orden_reglas_ids if rid in reglas_por_id]
        # Agregar las restantes si faltan
        restantes = [r for r in reglas_qs if str(r.id) not in orden_reglas_ids]
        reglas_ordenadas.extend(sorted(restantes, key=lambda x: (-x.prioridad, x.nombre)))
    else:
        reglas_ordenadas = list(reglas_qs.order_by("-prioridad", "nombre"))

    reglas = []
    for idx, r in enumerate(reglas_ordenadas):
        premisas = []
        for cond in r.condiciones.all().order_by("orden"):
            var_nombre = cond.variable.nombre if cond.variable else (cond.hecho.nombre if cond.hecho else "")
            premisas.append({
                "variable": var_nombre,
                "operador": cond.operador,
                "valor": cond.valor_esperado,
            })

        conclusiones = []
        for concl in r.conclusiones.all():
            var_nombre = (
                concl.variable_resultante.nombre
                if concl.variable_resultante
                else (concl.hecho_resultante.nombre if concl.hecho_resultante else "")
            )
            conclusiones.append({
                "variable": var_nombre,
                "valor": concl.valor_resultante,
            })

        reglas.append({
            "id": str(r.id),
            "nombre": r.nombre,
            "orden": idx,
            "prioridad": r.prioridad,
            "marcada": False,
            "disparada": False,
            "premisas": premisas,
            "conclusiones": conclusiones,
        })

    return {
        "sistema_experto_id": str(sistema_experto_id),
        "base_conocimiento_id": str(bc.id),
        "base_conocimiento_nombre": bc.nombre,
        "variables": variables,
        "hechos_iniciales": hechos_iniciales,
        "reglas": reglas,
    }


def instanciar_entorno_runtime(snapshot: Dict[str, Any]) -> tuple[List[ReglaRef], BaseHechosValue]:
    """
    Convierte el snapshot JSON en las estructuras de dominio de la Máquina Virtual
    (ReglaRef y BaseHechosValue).
    """
    bh = BaseHechosValue()
    for idx, h in enumerate(snapshot.get("hechos_iniciales", [])):
        bh.add(HechoValor(
            id=f"h_init_{idx}",
            variable_id=h.get("variable_id", f"v_{idx}"),
            variable_nombre=h.get("variable", ""),
            valor=h.get("valor"),
            tipo_dato=h.get("tipo_dato", "TEXTO"),
            origen=h.get("origen", "INICIAL"),
        ))

    reglas_refs = []
    for idx, r_data in enumerate(snapshot.get("reglas", [])):
        r_ref = ReglaRef(
            id=r_data["id"],
            nombre=r_data["nombre"],
            premisas=r_data.get("premisas", []),
            conclusiones=r_data.get("conclusiones", []),
            marcada=r_data.get("marcada", False),
            disparada=r_data.get("disparada", False),
            orden=idx,
        )
        reglas_refs.append(r_ref)

    return reglas_refs, bh
