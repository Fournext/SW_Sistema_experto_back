"""Autorización contextual: las capacidades de una actividad no cambian roles globales."""
import json
import copy
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.actividades.cursos_api import es_docente, es_estudiante, matricula_activa
from apps.actividades.models import AsignacionActividadModel, TrabajoActividadModel, EntregaActividadModel
from apps.sistemas_expertos.models import SistemaExpertoModel
from apps.base_conocimiento.models import BaseConocimientoModel

HERRAMIENTAS = ("ver_bc", "editar_bc", "editor_visual", "inferencia_directa", "simulacion", "validacion", "trazabilidad")


def permisos_actividad(actividad):
    creacion = actividad.tipo == "CREACION_BC"
    predeterminados = dict(zip(HERRAMIENTAS, (True, creacion, creacion, not creacion, not creacion, True, not creacion)))
    return {**predeterminados, **(actividad.permisos or {})}


def validar_permisos(tipo, permisos):
    if not isinstance(permisos, dict) or any(k not in HERRAMIENTAS or not isinstance(v, bool) for k, v in permisos.items()):
        raise ValidationError({"permisos": "Se requieren capacidades booleanas conocidas."})
    if tipo == "ANALISIS_BC" and permisos.get("editar_bc"):
        raise ValidationError({"permisos": "El análisis usa una base de conocimiento de solo lectura."})
    if permisos.get("editor_visual") and permisos.get("ver_bc") is False:
        raise ValidationError({"permisos": "El editor visual requiere acceso a la base de conocimiento."})


def fuente_docente(usuario, id_sistema):
    if not es_docente(usuario):
        raise PermissionDenied()
    sistemas = SistemaExpertoModel.objects.filter(trabajo_actividad__isnull=True)
    if not usuario.is_superuser:
        sistemas = sistemas.filter(Q(created_by_id=usuario.id) | Q(created_by__isnull=True))
    return get_object_or_404(sistemas, pk=id_sistema)


def asignacion_visible(usuario, id_asignacion, escritura=False):
    asignacion = get_object_or_404(AsignacionActividadModel.objects.select_related("curso", "actividad__sistema_experto"), pk=id_asignacion)
    if es_docente(usuario):
        if not usuario.is_superuser and (asignacion.curso.docente_id != usuario.id or asignacion.actividad.docente_id != usuario.id):
            raise NotFound()
    else:
        if not es_estudiante(usuario) or not matricula_activa(asignacion.curso, usuario):
            raise NotFound()
        actividad = asignacion.actividad
        if not actividad.activa or actividad.estado != "PUBLICADA" or asignacion.estado != "VIGENTE":
            raise NotFound()
        if actividad.sistema_experto_id and actividad.sistema_experto.estado != "ACTIVO":
            raise NotFound()
    if escritura:
        if not asignacion.curso.activo or asignacion.estado != "VIGENTE":
            raise PermissionDenied("El curso o la asignación están cerrados.")
        if asignacion.fecha_limite and asignacion.fecha_limite < timezone.now():
            raise PermissionDenied("El plazo de entrega ha vencido.")
        if EntregaActividadModel.objects.filter(asignacion=asignacion, estudiante=usuario, estado="ENVIADA").exists():
            raise PermissionDenied("La entrega está cerrada; el docente debe reabrirla.")
    return asignacion


@transaction.atomic
def sistema_trabajo(asignacion, usuario):
    if asignacion.actividad.tipo == "ANALISIS_BC":
        return asignacion.actividad.sistema_experto
    if not es_estudiante(usuario):
        raise PermissionDenied("El contenido de trabajo privado solo está disponible para su estudiante.")
    # Bloquear la asignación serializa la primera creación y evita duplicados huérfanos.
    AsignacionActividadModel.objects.select_for_update().get(pk=asignacion.pk)
    trabajo = TrabajoActividadModel.objects.filter(asignacion=asignacion, estudiante=usuario).select_related("sistema_experto").first()
    if trabajo:
        return trabajo.sistema_experto
    sistema = SistemaExpertoModel.objects.create(nombre=f"Trabajo - {asignacion.actividad.titulo}"[:150], estado="BORRADOR", created_by=usuario)
    BaseConocimientoModel.objects.create(sistema_experto=sistema, nombre=f"BC - {sistema.nombre}"[:150])
    TrabajoActividadModel.objects.create(asignacion=asignacion, estudiante=usuario, sistema_experto=sistema)
    return sistema


def json_seguro(datos):
    return json.loads(json.dumps(datos, cls=DjangoJSONEncoder))


def snapshot_bc(sistema):
    from apps.base_conocimiento.models import HechoModel, VariableModel, ReglaModel
    base = BaseConocimientoModel.objects.get(sistema_experto=sistema)
    reglas = []
    for regla in ReglaModel.objects.filter(base_conocimiento=base).prefetch_related("condiciones", "conclusiones").order_by("-prioridad", "nombre", "id"):
        datos = {"id": regla.id, "nombre": regla.nombre, "descripcion": regla.descripcion, "prioridad": regla.prioridad,
                 "factor_certeza": regla.factor_certeza, "activa": regla.activa}
        datos["condiciones"] = list(regla.condiciones.order_by("orden", "id").values())
        datos["conclusiones"] = list(regla.conclusiones.order_by("id").values())
        reglas.append(datos)
    return json_seguro({"id": base.id, "sistema_experto_id": sistema.id, "nombre": base.nombre, "version": base.version,
                        "hechos": list(HechoModel.objects.filter(base_conocimiento=base).values()),
                        "variables": list(VariableModel.objects.filter(base_conocimiento=base).values()), "reglas": reglas})


def redactar_resultado(datos, permisos):
    """Aplicar la política vigente al leer; nunca modificar el snapshot almacenado."""
    ver_bc = permisos.get("ver_bc", False)
    traza = permisos.get("trazabilidad", False)
    ocultos = {"detalles", "reglas_evaluadas", "reglas_activadas", "reglas_disparadas", "reglas_involucradas",
               "condiciones_evaluadas", "condiciones_cumplidas", "cadena_razonamiento", "arbol", "texto",
               "regla_id", "regla_nombre", "regla_origen_id", "regla_origen_nombre", "regla_disparada_id",
               "siguiente_regla", "pasos", "paso", "conflictos"}
    if not traza:
        ocultos |= {"explicacion", "resumen_explicativo"}
    def filtrar(valor):
        if isinstance(valor, list):
            return [filtrar(v) for v in valor]
        if not isinstance(valor, dict):
            return valor
        resultado = {}
        for k, v in valor.items():
            if not traza and k in ocultos:
                continue
            if not ver_bc and k in ("bc", "bc_snapshot"):
                resultado[k] = {a: b for a, b in v.items() if a in ("id", "sistema_experto_id", "nombre", "version")} if isinstance(v, dict) else None
            elif not ver_bc and k in ("reglas", "condiciones", "conclusiones"):
                continue
            else:
                resultado[k] = filtrar(v)
        return resultado
    return filtrar(copy.deepcopy(datos))


def dominio_snapshot(datos):
    from dataclasses import fields
    from uuid import UUID
    from apps.base_conocimiento.entities import Hecho, Variable, Regla, Condicion, Conclusion
    def entidad(clase, fila):
        atributos = {f.name for f in fields(clase)}
        fila = {k: v for k, v in fila.items() if k in atributos}
        for k, v in list(fila.items()):
            if v and (k == "id" or k.endswith("_id")):
                fila[k] = UUID(str(v))
        return clase(**fila)
    hechos = [entidad(Hecho, h) for h in datos.get("hechos", [])]
    variables = [entidad(Variable, v) for v in datos.get("variables", [])]
    reglas = []
    for fila in datos.get("reglas", []):
        regla = entidad(Regla, {k: v for k, v in fila.items() if k not in ("condiciones", "conclusiones")})
        regla.condiciones = [entidad(Condicion, c) for c in fila.get("condiciones", [])]
        regla.conclusiones = [entidad(Conclusion, c) for c in fila.get("conclusiones", [])]
        reglas.append(regla)
    return hechos, variables, reglas
