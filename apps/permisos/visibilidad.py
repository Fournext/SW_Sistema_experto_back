"""Visibilidad de sistemas en borrador, incluidos sus recursos por UUID."""
from uuid import UUID
from django.db.models import Q

from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission


def puede_ver_borradores(request):
    if getattr(request, "_actividad_context", None):
        return True
    if not hasattr(request, "_puede_ver_borradores"):
        usuario = request.user
        request._puede_ver_borradores = bool(usuario and usuario.is_authenticated and (
            usuario.is_superuser or usuario.groups.filter(name="Docente").exists()
        ))
    return request._puede_ver_borradores


class SistemaPublicadoPermission(BasePermission):
    """Un UUID de un descendiente nunca permite saltarse el estado del sistema."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request, "_actividad_context", None):
            return True
        docente = puede_ver_borradores(request)

        from apps.sistemas_expertos.models import SistemaExpertoModel
        from apps.base_conocimiento.models import (
            BaseConocimientoModel, HechoModel, VariableModel, ReglaModel, CondicionModel, ConclusionModel,
        )
        from apps.editor_visual.models import NodoVisualModel, ConexionVisualModel
        from apps.inferencia.models import EjecucionInferenciaModel
        from apps.validacion.models import ValidacionBaseModel
        from apps.actividades.models import ActividadEducativaModel, AsignacionActividadModel

        recursos = {
            "sistemas-expertos": (SistemaExpertoModel, "estado"),
            "bases-conocimiento": (BaseConocimientoModel, "sistema_experto__estado"),
            "hechos": (HechoModel, "base_conocimiento__sistema_experto__estado"),
            "variables": (VariableModel, "base_conocimiento__sistema_experto__estado"),
            "reglas": (ReglaModel, "base_conocimiento__sistema_experto__estado"),
            "condiciones": (CondicionModel, "regla__base_conocimiento__sistema_experto__estado"),
            "conclusiones": (ConclusionModel, "regla__base_conocimiento__sistema_experto__estado"),
            "nodos": (NodoVisualModel, "sistema_experto__estado"),
            "conexiones": (ConexionVisualModel, "sistema_experto__estado"),
            "inferencias": (EjecucionInferenciaModel, "sistema_experto__estado"),
            "simulaciones": (EjecucionInferenciaModel, "sistema_experto__estado"),
            "ejecuciones": (EjecucionInferenciaModel, "sistema_experto__estado"),
            "validaciones": (ValidacionBaseModel, "base_conocimiento__sistema_experto__estado"),
            "actividades": (ActividadEducativaModel, "sistema_experto__estado"),
            "asignaciones": (AsignacionActividadModel, "actividad__sistema_experto__estado"),
        }
        segmentos = request.path.strip("/").split("/")
        recurso = segmentos[2] if segmentos[:2] == ["api", "v1"] and len(segmentos) > 2 else None
        identificador = view.kwargs.get("id") or view.kwargs.get("id_actividad") or view.kwargs.get("id_asignacion")
        if recurso in recursos and recurso not in ("actividades", "asignaciones"):
            if identificador:
                from apps.actividades.trabajo_api import sistema_recurso
                sistema_id = sistema_recurso(recurso, identificador)
                sistema = SistemaExpertoModel.objects.get(pk=sistema_id)
                if hasattr(sistema, "trabajo_actividad"):
                    raise NotFound()
                if not docente and (sistema.estado == "BORRADOR" or sistema.actividades.exists()):
                    raise NotFound()
                if docente and sistema.created_by_id and sistema.created_by_id != request.user.id and not request.user.is_superuser:
                    raise NotFound()
                if recurso in ("inferencias", "simulaciones", "ejecuciones") and EjecucionInferenciaModel.objects.filter(pk=identificador, asignacion_id__isnull=False).exists():
                    raise NotFound()
            if identificador or recurso not in ("inferencias", "historial-inferencias"):
                return True
        if recurso in ("inferencias", "historial-inferencias") and not docente:
            sistema_id = request.query_params.get("sistema_id") or request.query_params.get("sistema_experto_id")
            if sistema_id:
                try:
                    sistema_id = UUID(sistema_id)
                except (ValueError, TypeError):
                    raise NotFound()
                if SistemaExpertoModel.objects.filter(pk=sistema_id).filter(
                    Q(estado="BORRADOR") | Q(actividades__isnull=False) | Q(trabajo_actividad__isnull=False)
                ).exists():
                    raise NotFound()
        if docente:
            return True
        if identificador and recurso in recursos:
            modelo, campo_estado = recursos[recurso]
            estado = modelo.objects.filter(pk=identificador).values_list(campo_estado, flat=True).first()
            if estado == "BORRADOR":
                raise NotFound()
        elif recurso in ("inferencias", "historial-inferencias"):
            sistema_id = request.query_params.get("sistema_id") or request.query_params.get("sistema_experto_id")
            if sistema_id:
                try:
                    sistema_id = UUID(sistema_id)
                except (ValueError, TypeError):
                    raise NotFound()
                if SistemaExpertoModel.objects.filter(pk=sistema_id, estado="BORRADOR").exists():
                    raise NotFound()
        # Las creaciones de actividades/asignaciones no tienen UUID en la ruta;
        # tampoco pueden recuperar un borrador mediante una FK enviada en el cuerpo.
        relaciones = {"actividades": ("sistema_experto_id", SistemaExpertoModel, "estado"),
                      "asignaciones": ("actividad_id", ActividadEducativaModel, "sistema_experto__estado")}
        if recurso in relaciones and request.method == "POST":
            campo, modelo, campo_estado = relaciones[recurso]
            valor = request.data.get(campo)
            if valor:
                try:
                    identificador_relacion = UUID(str(valor))
                except (ValueError, TypeError):
                    raise NotFound()
                if modelo.objects.filter(pk=identificador_relacion, **{campo_estado: "BORRADOR"}).exists():
                    raise NotFound()
        return True
