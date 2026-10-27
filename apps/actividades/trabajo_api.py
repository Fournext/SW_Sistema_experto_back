"""Adaptador de herramientas existentes con ámbito de asignación y estudiante."""
import json
from uuid import UUID
from django.db import transaction
from django.urls import resolve, Resolver404
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.actividades.cursos_api import es_docente
from apps.actividades.politicas import (asignacion_visible, sistema_trabajo, permisos_actividad, snapshot_bc,
                                     redactar_resultado, json_seguro)
from apps.base_conocimiento.models import (BaseConocimientoModel, HechoModel, VariableModel, ReglaModel, CondicionModel, ConclusionModel)
from apps.editor_visual.models import NodoVisualModel, ConexionVisualModel
from apps.sistemas_expertos.models import SistemaExpertoModel
from apps.inferencia.models import EjecucionInferenciaModel
from apps.validacion.models import ValidacionBaseModel
from compartido.respuestas.respuesta_api import respuesta_exitosa, respuesta_error


def sistema_recurso(recurso, id_recurso):
    modelos = {
        "sistemas-expertos": (SistemaExpertoModel, "id"), "bases-conocimiento": (BaseConocimientoModel, "sistema_experto_id"),
        "hechos": (HechoModel, "base_conocimiento__sistema_experto_id"), "variables": (VariableModel, "base_conocimiento__sistema_experto_id"),
        "reglas": (ReglaModel, "base_conocimiento__sistema_experto_id"), "condiciones": (CondicionModel, "regla__base_conocimiento__sistema_experto_id"),
        "conclusiones": (ConclusionModel, "regla__base_conocimiento__sistema_experto_id"),
        "nodos": (NodoVisualModel, "sistema_experto_id"), "conexiones": (ConexionVisualModel, "sistema_experto_id"),
        "inferencias": (EjecucionInferenciaModel, "sistema_experto_id"), "simulaciones": (EjecucionInferenciaModel, "sistema_experto_id"),
        "ejecuciones": (EjecucionInferenciaModel, "sistema_experto_id"), "validaciones": (ValidacionBaseModel, "base_conocimiento__sistema_experto_id"),
    }
    if recurso not in modelos:
        raise NotFound()
    modelo, campo = modelos[recurso]
    id_sistema = modelo.objects.filter(pk=id_recurso).values_list(campo, flat=True).first()
    if id_sistema is None:
        raise NotFound()
    return id_sistema


def _capacidad(ruta, metodo):
    partes = ruta.strip("/").split("/")
    prefijo = partes[0]
    lectura = metodo in ("GET", "HEAD", "OPTIONS")
    if prefijo == "sistemas-expertos":
        if len(partes) == 2 and lectura:
            return "metadata"
        if "base-conocimiento" in partes and lectura:
            return "metadata"
        if "inferencias" in partes:
            return "inferencia_directa"
        if "simulaciones" in partes:
            return "simulacion"
        if any(p in partes for p in ("editor", "nodos", "conexiones")):
            return "editor_visual"
    if prefijo in ("bases-conocimiento", "validaciones") and any(p in partes for p in ("validar", "validaciones")):
        return "validacion"
    if prefijo in ("hechos", "variables", "reglas", "condiciones", "conclusiones", "bases-conocimiento"):
        return "ver_bc" if lectura else "editar_bc"
    if prefijo in ("nodos", "conexiones"):
        return "editor_visual"
    if prefijo in ("inferencias", "simulaciones", "ejecuciones", "historial-inferencias"):
        if any(p in partes for p in ("detalles", "pasos", "conflictos", "explicacion")):
            return "trazabilidad"
        return "ejecucion" if lectura else "simulacion"
    raise NotFound()


def entradas_sistema(sistema):
    base = BaseConocimientoModel.objects.get(sistema_experto=sistema)
    entradas = {}
    for h in HechoModel.objects.filter(base_conocimiento=base):
        if h.es_inicial or (h.pregunta and h.pregunta.strip()):
            entradas[h.nombre.lower().strip()] = {"id": str(h.id), "nombre": h.nombre, "tipo_dato": h.tipo_dato,
                "valor": h.valor, "pregunta": h.pregunta, "opciones": h.opciones}
    for v in VariableModel.objects.filter(base_conocimiento=base):
        if v.es_inicial or (v.pregunta and v.pregunta.strip()):
            entradas.setdefault(v.nombre.lower().strip(), {"id": str(v.id), "nombre": v.nombre,
                "tipo_dato": v.tipo_dato, "valor": v.valor_defecto, "pregunta": v.pregunta, "opciones": []})
    return list(entradas.values())


class TrabajoActividadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def _procesar(self, request, id_asignacion, ruta):
        escritura = request.method not in ("GET", "HEAD", "OPTIONS")
        a = asignacion_visible(request.user, id_asignacion, escritura=escritura)
        if es_docente(request.user):
            raise PermissionDenied("La revisión docente usa las entregas enviadas, no el trabajo privado.")
        sistema = sistema_trabajo(a, request.user)
        permisos = permisos_actividad(a.actividad)
        if ruta.strip("/") == "entradas":
            if request.method != "GET" or not (permisos["inferencia_directa"] or permisos["simulacion"]):
                raise PermissionDenied()
            return respuesta_exitosa(datos=entradas_sistema(sistema))
        capacidad = _capacidad(ruta, request.method)
        if capacidad == "ejecucion":
            permitido = permisos["inferencia_directa"] or permisos["simulacion"]
        else:
            permitido = capacidad == "metadata" or permisos.get(capacidad, False)
        if capacidad == "validacion" and escritura and (permisos["inferencia_directa"] or permisos["simulacion"]):
            permitido = True  # Prevalidación interna de inferencia; no habilita la pantalla de reportes.
        if not permitido:
            raise PermissionDenied("Esta herramienta no está habilitada para la actividad.")
        if capacidad == "editor_visual" and (not permisos["ver_bc"] or escritura and not permisos["editar_bc"]):
            raise PermissionDenied()
        if capacidad == "editar_bc" and a.actividad.tipo != "CREACION_BC":
            raise PermissionDenied()
        path = "/api/v1/" + ruta.strip("/") + "/"
        try:
            destino = resolve(path)
        except Resolver404:
            raise NotFound()
        if destino.namespace not in ("sistemas_expertos", "base_conocimiento", "editor_visual", "inferencia", "validacion"):
            raise NotFound()
        prefijo = ruta.strip("/").split("/")[0]
        identificador = destino.kwargs.get("id")
        if identificador:
            if sistema_recurso(prefijo, identificador) != sistema.id:
                raise NotFound()
            if prefijo in ("inferencias", "simulaciones", "ejecuciones"):
                ejecucion = EjecucionInferenciaModel.objects.get(pk=identificador)
                if ejecucion.asignacion_id != a.id or ejecucion.estudiante_id != request.user.id:
                    raise NotFound()
                if ejecucion.es_simulacion and capacidad == "ejecucion" and not permisos["simulacion"]:
                    raise PermissionDenied()
                if not ejecucion.es_simulacion and capacidad == "ejecucion" and not permisos["inferencia_directa"]:
                    raise PermissionDenied()
        elif prefijo not in ("inferencias", "historial-inferencias"):
            raise NotFound()
        datos = request.data if escritura else None
        if escritura:
            relaciones = {"hecho_id": "hechos", "variable_id": "variables", "regla_id": "reglas",
                "hecho_resultante_id": "hechos", "variable_resultante_id": "variables", "nodo_origen_id": "nodos",
                "nodo_destino_id": "nodos", "base_conocimiento_id": "bases-conocimiento"}
            if datos.get("referencia_id"):
                relaciones["referencia_id"] = {"HECHO": "hechos", "VARIABLE": "variables", "REGLA": "reglas",
                                              "CONDICION": "condiciones", "CONCLUSION": "conclusiones"}.get(datos.get("tipo"), "")
            for campo, recurso in relaciones.items():
                if datos.get(campo):
                    try:
                        id_referencia = UUID(str(datos[campo]))
                    except (TypeError, ValueError):
                        raise ValidationError({campo: "UUID inválido."})
                    if sistema_recurso(recurso, id_referencia) != sistema.id:
                        raise NotFound()
        factory = APIRequestFactory()
        query = request.query_params.copy()
        if prefijo in ("inferencias", "historial-inferencias") and identificador is None:
            query["sistema_id"] = str(sistema.id)
        if escritura:
            interna = factory.generic(request.method, path, json.dumps(datos), content_type="application/json")
        else:
            interna = factory.get(path, query)
        force_authenticate(interna, user=request.user)
        interna._actividad_context = {"asignacion_id": a.id, "estudiante_id": request.user.id, "sistema_id": sistema.id}
        antes = snapshot_bc(sistema) if capacidad in ("inferencia_directa", "simulacion") and escritura else None
        respuesta = destino.func(interna, **destino.kwargs)
        if respuesta.status_code >= 400:
            if not permisos["ver_bc"]:
                return respuesta_error(mensaje="No se pudo completar la operación de la actividad.", codigo_estado=respuesta.status_code)
            return respuesta
        contenido = respuesta.data.get("data") if isinstance(respuesta.data, dict) else None
        if contenido is None:
            return respuesta
        if escritura and isinstance(contenido, dict) and capacidad in ("inferencia_directa", "simulacion"):
            ejecucion_id = contenido.get("id") or contenido.get("ejecucion_id")
            if ejecucion_id:
                qs = EjecucionInferenciaModel.objects.filter(pk=ejecucion_id, sistema_experto=sistema)
                if identificador is not None and prefijo in ("simulaciones", "inferencias", "ejecuciones"):
                    # La BC usada al iniciar la sesión permanece estable a lo largo de sus pasos.
                    qs.update(asignacion=a, estudiante=request.user)
                else:
                    qs.update(asignacion=a, estudiante=request.user, bc_snapshot=antes)
        if prefijo in ("inferencias", "historial-inferencias") and identificador is None and isinstance(contenido, list):
            ids = set(str(i) for i in EjecucionInferenciaModel.objects.filter(asignacion=a, estudiante=request.user).values_list("id", flat=True))
            contenido = [e for e in contenido if str(e.get("id")) in ids]
        if capacidad == "metadata" and not permisos["ver_bc"]:
            contenido = {k: v for k, v in contenido.items() if k in ("id", "nombre", "estado", "sistema_experto_id", "version", "creada_en", "actualizada_en")}
        if capacidad == "validacion" and (not permisos["ver_bc"] or not permisos["validacion"]):
            contenido = {k: v for k, v in contenido.items() if k in ("id", "es_valida", "total_errores", "total_advertencias", "fecha_validacion")}
        contenido = redactar_resultado(contenido, permisos)
        respuesta.data["data"] = contenido
        return respuesta

    def get(self, request, id_asignacion, ruta):
        return self._procesar(request, id_asignacion, ruta)

    post = get
    patch = get
    put = get
    delete = get
