"""Actividades por curso, entregas con revisiones y retroalimentación sin notas."""
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.actividades.cursos_api import es_docente, curso_docente
from apps.actividades.models import (ActividadEducativaModel, AsignacionActividadModel, EntregaActividadModel,
                                    MatriculaCursoModel, RevisionEntregaModel, ComentarioEntregaModel)
from apps.actividades.politicas import (asignacion_visible, permisos_actividad, validar_permisos, fuente_docente,
                                     sistema_trabajo, snapshot_bc, json_seguro)
from compartido.respuestas.respuesta_api import respuesta_creada, respuesta_exitosa


class ActividadEntrada(serializers.Serializer):
    titulo = serializers.CharField(max_length=200)
    instrucciones = serializers.CharField()
    tipo = serializers.ChoiceField(choices=["ANALISIS_BC", "CREACION_BC"], default="ANALISIS_BC")
    sistema_experto_id = serializers.UUIDField(required=False, allow_null=True)
    dificultad = serializers.ChoiceField(choices=["BASICA", "MEDIA", "AVANZADA"], default="MEDIA")
    estado = serializers.ChoiceField(choices=["BORRADOR", "PUBLICADA", "INACTIVA"], default="BORRADOR")
    permisos = serializers.DictField(child=serializers.BooleanField(), required=False)
    curso_id = serializers.UUIDField(required=False)
    activa = serializers.BooleanField(required=False)


def datos_actividad(a):
    return {"id": str(a.id), "docente_id": a.docente_id, "docente_username": a.docente.username,
            "sistema_experto_id": str(a.sistema_experto_id) if a.sistema_experto_id else None,
            "sistema_experto_nombre": a.sistema_experto.nombre if a.sistema_experto_id else None,
            "titulo": a.titulo, "instrucciones": a.instrucciones, "tipo": a.tipo, "permisos": permisos_actividad(a),
            "dificultad": a.dificultad, "estado": a.estado, "activa": a.activa,
            "creada_en": a.creada_en, "actualizada_en": a.actualizada_en}


def asignaciones_usuario(usuario):
    qs = AsignacionActividadModel.objects.select_related("actividad__docente", "actividad__sistema_experto", "curso")
    if es_docente(usuario):
        return qs.filter(actividad__activa=True) if usuario.is_superuser else qs.filter(curso__docente=usuario, actividad__docente=usuario, actividad__activa=True)
    return qs.filter(curso__matriculas__estudiante=usuario, curso__matriculas__activo=True,
                     actividad__activa=True, actividad__estado="PUBLICADA", estado="VIGENTE").filter(
        Q(actividad__sistema_experto__estado="ACTIVO") | Q(actividad__tipo="CREACION_BC", actividad__sistema_experto__isnull=True)
    ).distinct()


def datos_asignacion(a):
    return {"id": str(a.id), "actividad_id": str(a.actividad_id), "actividad_titulo": a.actividad.titulo,
            "curso_id": str(a.curso_id), "curso_codigo": a.curso.codigo, "curso_nombre": a.curso.nombre,
            "fecha_asignacion": a.fecha_asignacion, "fecha_limite": a.fecha_limite, "estado": a.estado,
            "tipo": a.actividad.tipo}


def _docente_actividad(usuario, id_actividad):
    if not es_docente(usuario):
        raise PermissionDenied()
    qs = ActividadEducativaModel.objects.select_related("docente", "sistema_experto")
    if not usuario.is_superuser:
        qs = qs.filter(docente=usuario)
    return get_object_or_404(qs, pk=id_actividad)


def _guardar_actividad(usuario, datos, actividad=None):
    if not es_docente(usuario):
        raise PermissionDenied()
    tipo = datos.get("tipo", actividad.tipo if actividad else "ANALISIS_BC")
    if actividad and tipo != actividad.tipo and actividad.asignaciones.exists():
        raise ValidationError({"tipo": "No se cambia el tipo de una actividad ya asignada."})
    fuente_id = datos.get("sistema_experto_id", actividad.sistema_experto_id if actividad else None)
    fuente = fuente_docente(usuario, fuente_id) if fuente_id else None
    estado = datos.get("estado", actividad.estado if actividad else "BORRADOR")
    if tipo == "ANALISIS_BC" and fuente is None:
        raise ValidationError({"sistema_experto_id": "El análisis requiere una base de conocimiento fuente."})
    if estado == "PUBLICADA" and fuente and fuente.estado != "ACTIVO":
        raise ValidationError({"sistema_experto_id": "La fuente debe estar activa para publicar."})
    permisos = datos.get("permisos", actividad.permisos if actividad else {})
    validar_permisos(tipo, permisos)
    campos = {k: v for k, v in datos.items() if k not in ("sistema_experto_id", "curso_id", "permisos")}
    campos.update(tipo=tipo, sistema_experto=fuente, permisos=permisos)
    if actividad is None:
        return ActividadEducativaModel.objects.create(docente=usuario, **campos)
    for k, v in campos.items():
        setattr(actividad, k, v)
    actividad.save()
    return actividad


class ActividadesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ActividadEducativaModel.objects.filter(activa=True).select_related("docente", "sistema_experto")
        if es_docente(request.user):
            if not request.user.is_superuser:
                qs = qs.filter(docente=request.user)
        else:
            qs = qs.filter(asignaciones__in=asignaciones_usuario(request.user)).distinct()
        if request.query_params.get("estado"):
            qs = qs.filter(estado=request.query_params["estado"])
        return respuesta_exitosa(datos=[datos_actividad(a) for a in qs])

    @transaction.atomic
    def post(self, request):
        ser = ActividadEntrada(data=request.data)
        ser.is_valid(raise_exception=True)
        actividad = _guardar_actividad(request.user, ser.validated_data)
        datos = datos_actividad(actividad)
        if ser.validated_data.get("curso_id"):
            curso = curso_docente(request.user, ser.validated_data["curso_id"])
            if not curso.activo:
                raise PermissionDenied("El curso está archivado.")
            a = AsignacionActividadModel.objects.create(actividad=actividad, curso=curso)
            datos["asignacion_id"] = str(a.id)
        return respuesta_creada(datos=datos)


class ActividadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id_actividad):
        if es_docente(request.user):
            actividad = _docente_actividad(request.user, id_actividad)
        else:
            a = get_object_or_404(asignaciones_usuario(request.user), actividad_id=id_actividad)
            actividad = a.actividad
        return respuesta_exitosa(datos=datos_actividad(actividad))

    def patch(self, request, id_actividad):
        actividad = _docente_actividad(request.user, id_actividad)
        ser = ActividadEntrada(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return respuesta_exitosa(datos=datos_actividad(_guardar_actividad(request.user, ser.validated_data, actividad)))

    put = patch

    def delete(self, request, id_actividad):
        actividad = _docente_actividad(request.user, id_actividad)
        if not actividad.asignaciones.exists():
            actividad.delete()
            return respuesta_exitosa(datos=None, mensaje="Actividad eliminada exitosamente.")
        actividad.activa = False
        actividad.save(update_fields=["activa"])
        return respuesta_exitosa(datos=datos_actividad(actividad), mensaje="Actividad eliminada exitosamente.")


class AsignacionEntrada(serializers.Serializer):
    actividad_id = serializers.UUIDField()
    curso_id = serializers.UUIDField()
    fecha_limite = serializers.DateTimeField(required=False, allow_null=True)
    estado = serializers.ChoiceField(choices=["VIGENTE", "CERRADA", "CANCELADA"], required=False)


class AsignacionesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = asignaciones_usuario(request.user)
        for campo in ("curso_id", "actividad_id", "estado"):
            if request.query_params.get(campo):
                qs = qs.filter(**{campo: request.query_params[campo]})
        return respuesta_exitosa(datos=[datos_asignacion(a) for a in qs])

    def post(self, request):
        ser = AsignacionEntrada(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        actividad = _docente_actividad(request.user, d["actividad_id"])
        curso = curso_docente(request.user, d["curso_id"])
        if not curso.activo:
            raise PermissionDenied("El curso está archivado.")
        if AsignacionActividadModel.objects.filter(actividad=actividad, curso=curso).exists():
            raise ValidationError("La actividad ya está asignada a este curso.")
        a = AsignacionActividadModel.objects.create(actividad=actividad, curso=curso,
                                                   fecha_limite=d.get("fecha_limite"), estado=d.get("estado", "VIGENTE"))
        return respuesta_creada(datos=datos_asignacion(a))


class ContextoAsignacionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id_asignacion):
        a = asignacion_visible(request.user, id_asignacion)
        entrega = EntregaActividadModel.objects.filter(asignacion=a, estudiante=request.user).first()
        sistema = sistema_trabajo(a, request.user) if not es_docente(request.user) else a.actividad.sistema_experto
        writable = not es_docente(request.user)
        try:
            asignacion_visible(request.user, id_asignacion, escritura=True)
        except PermissionDenied:
            writable = False
        return respuesta_exitosa(datos={**datos_asignacion(a), "actividad": datos_actividad(a.actividad),
            "curso": {"id": str(a.curso_id), "codigo": a.curso.codigo, "nombre": a.curso.nombre, "activo": a.curso.activo},
            "permisos": permisos_actividad(a.actividad), "entrega": datos_entrega(entrega, incluir_contenido=False) if entrega else None,
            "trabajo_sistema_id": str(sistema.id) if sistema else None, "puede_editar": writable})

    def patch(self, request, id_asignacion):
        a = asignacion_visible(request.user, id_asignacion)
        if not es_docente(request.user):
            raise PermissionDenied()
        ser = AsignacionEntrada(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        if any(k in ser.validated_data for k in ("actividad_id", "curso_id")):
            raise ValidationError("No se cambia la actividad o curso de una asignación existente.")
        for k, v in ser.validated_data.items():
            setattr(a, k, v)
        a.save()
        return respuesta_exitosa(datos=datos_asignacion(a))


class ActividadesEstudianteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = asignaciones_usuario(request.user)
        entregas = {e.asignacion_id: e for e in EntregaActividadModel.objects.filter(asignacion__in=qs, estudiante=request.user)}
        return respuesta_exitosa(datos=[{**datos_asignacion(a), "asignacion_id": str(a.id),
            "tipo": a.actividad.tipo, "permisos": permisos_actividad(a.actividad),
            "estado_asignacion": a.estado, "tiene_entrega": a.id in entregas,
            "estado_entrega": entregas[a.id].estado if a.id in entregas else "PENDIENTE",
            "entrega_id": str(entregas[a.id].id) if a.id in entregas else None} for a in qs])


def datos_entrega(entrega, incluir_contenido=True, usuario=None):
    if entrega is None:
        return None
    datos = {"id": str(entrega.id), "entrega_id": str(entrega.id), "asignacion_id": str(entrega.asignacion_id),
        "estudiante_id": entrega.estudiante_id, "estudiante_username": entrega.estudiante.username,
        "estado": entrega.estado, "fecha_envio": entrega.fecha_envio, "numero_revision": entrega.numero_revision,
        "creada_en": entrega.creada_en, "actualizada_en": entrega.actualizada_en}
    if incluir_contenido:
        if not (usuario is not None and es_docente(usuario) and entrega.estado != "ENVIADA"):
            datos.update(solucion_texto=entrega.solucion_texto, hechos_ingresados=entrega.hechos_ingresados,
                         ejecuciones_ids=entrega.ejecuciones_ids,
                         ejecucion_inferencia_id=str(entrega.ejecucion_inferencia_id) if entrega.ejecucion_inferencia_id else None)
        datos["revisiones"] = [{"id": str(r.id), "numero": r.numero, "snapshot": r.snapshot, "creada_en": r.creada_en,
            "comentarios": [{"id": str(c.id), "revision_id": str(r.id), "autor_id": c.autor_id,
                             "autor_nombre": c.autor.nombre_completo or c.autor.username, "texto": c.texto, "creado_en": c.creado_en}
                            for c in r.comentarios.select_related("autor").all()]} for r in entrega.revisiones.all()]
    if incluir_contenido and usuario is not None and not es_docente(usuario):
        from apps.actividades.politicas import redactar_resultado
        datos["revisiones"] = [{**r, "snapshot": redactar_resultado(r["snapshot"], permisos_actividad(entrega.asignacion.actividad))}
                               for r in datos["revisiones"]]
    return datos


class EntregaEntrada(serializers.Serializer):
    solucion_texto = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    hechos_ingresados = serializers.ListField(child=serializers.DictField(), required=False)
    ejecucion_inferencia_id = serializers.UUIDField(required=False, allow_null=True)
    ejecuciones_ids = serializers.ListField(child=serializers.UUIDField(), required=False)


def _ejecuciones_adjuntas(usuario, a, datos, entrega):
    from apps.inferencia.models import EjecucionInferenciaModel
    ids = [str(i) for i in datos.get("ejecuciones_ids", entrega.ejecuciones_ids)]
    principal = datos.get("ejecucion_inferencia_id", entrega.ejecucion_inferencia_id)
    if principal:
        ids = list(set(ids + [str(principal)]))
    qs = EjecucionInferenciaModel.objects.filter(id__in=ids, asignacion=a, estudiante=usuario)
    if qs.count() != len(set(ids)):
        raise ValidationError("Las ejecuciones adjuntas deben pertenecer al estudiante y a esta asignación.")
    return list(qs.order_by("fecha_inicio"))


def _snapshot_ejecucion(e):
    return json_seguro({"id": e.id, "estado": e.estado, "conclusion_final": e.conclusion_final, "es_simulacion": e.es_simulacion,
        "bc_snapshot": e.bc_snapshot, "hechos_iniciales_snapshot": e.hechos_iniciales_snapshot,
        "detalles": list(e.detalles.order_by("orden").values()), "pasos": list(e.pasos.order_by("numero_paso").values()),
        "hechos_generados": list(e.hechos_inferidos.order_by("orden").values())})


class EntregaEstudianteV2APIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id_asignacion):
        a = asignacion_visible(request.user, id_asignacion)
        if es_docente(request.user):
            raise PermissionDenied("Use la lista de entregas enviadas para revisar el trabajo.")
        entrega = EntregaActividadModel.objects.filter(asignacion=a, estudiante=request.user).first()
        return respuesta_exitosa(datos=datos_entrega(entrega, usuario=request.user))

    @transaction.atomic
    def post(self, request, id_asignacion, enviar=False):
        a = asignacion_visible(request.user, id_asignacion, escritura=True)
        if es_docente(request.user):
            raise PermissionDenied()
        ser = EntregaEntrada(data=request.data)
        ser.is_valid(raise_exception=True)
        entrega, _ = EntregaActividadModel.objects.select_for_update().get_or_create(asignacion=a, estudiante=request.user)
        d = ser.validated_data
        ejecuciones = _ejecuciones_adjuntas(request.user, a, d, entrega)
        entrega.ejecuciones_ids = [str(e.id) for e in ejecuciones]
        for campo in ("solucion_texto", "hechos_ingresados", "ejecucion_inferencia_id"):
            if campo in d:
                setattr(entrega, campo, d[campo])
        if enviar:
            if not entrega.solucion_texto and not entrega.hechos_ingresados and not ejecuciones and a.actividad.tipo != "CREACION_BC":
                raise ValidationError("Agregue una justificación, datos o una ejecución antes de enviar.")
            sistema = sistema_trabajo(a, request.user)
            bc = ejecuciones[-1].bc_snapshot if ejecuciones and a.actividad.tipo == "ANALISIS_BC" else snapshot_bc(sistema)
            entrega.numero_revision += 1
            entrega.estado = "ENVIADA"
            entrega.fecha_envio = timezone.now()
            entrega.save()
            RevisionEntregaModel.objects.create(entrega=entrega, numero=entrega.numero_revision, snapshot=json_seguro({
                "solucion_texto": entrega.solucion_texto, "hechos_ingresados": entrega.hechos_ingresados, "bc": bc,
                "ejecuciones": [_snapshot_ejecucion(e) for e in ejecuciones], "tipo": a.actividad.tipo, "permisos": permisos_actividad(a.actividad)}))
        else:
            entrega.save()
        return respuesta_exitosa(datos=datos_entrega(entrega, usuario=request.user))


class EnviarEntregaV2APIView(EntregaEstudianteV2APIView):
    def post(self, request, id_asignacion):
        return super().post(request, id_asignacion, enviar=True)


class EntregasDocenteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id_asignacion):
        a = asignacion_visible(request.user, id_asignacion)
        if not es_docente(request.user):
            raise PermissionDenied()
        entregas = {e.estudiante_id: e for e in EntregaActividadModel.objects.filter(asignacion=a).select_related("estudiante")}
        miembros = MatriculaCursoModel.objects.filter(curso=a.curso).select_related("estudiante")
        filas = []
        for m in miembros:
            e = entregas.get(m.estudiante_id)
            filas.append({"estudiante_id": m.estudiante_id, "estudiante_username": m.estudiante.username,
                "estudiante_nombre": m.estudiante.nombre_completo, "matricula_activa": m.activo,
                "estado": e.estado if e else "PENDIENTE", "entrega_id": str(e.id) if e else None,
                "fecha_envio": e.fecha_envio if e else None, "numero_revision": e.numero_revision if e else 0})
        return respuesta_exitosa(datos=filas)


def _entrega_visible(usuario, id_entrega):
    e = get_object_or_404(EntregaActividadModel.objects.select_related("estudiante", "asignacion__curso", "asignacion__actividad"), pk=id_entrega)
    asignacion_visible(usuario, e.asignacion_id)
    if es_docente(usuario):
        if e.estado != "ENVIADA" and not e.revisiones.exists():
            raise NotFound()
    elif e.estudiante_id != usuario.id:
        raise NotFound()
    return e


class EntregaDetailV2APIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id_entrega):
        return respuesta_exitosa(datos=datos_entrega(_entrega_visible(request.user, id_entrega), usuario=request.user))


class ComentarioEntregaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id_entrega):
        if not es_docente(request.user):
            raise PermissionDenied("Solo el docente puede comentar una entrega enviada.")
        e = _entrega_visible(request.user, id_entrega)
        if e.estado != "ENVIADA":
            raise PermissionDenied("Solo se comenta una entrega enviada.")
        texto = request.data.get("texto", "")
        if not isinstance(texto, str) or not texto.strip():
            raise ValidationError({"texto": "Escriba un comentario."})
        revision = e.revisiones.filter(id=request.data["revision_id"]).first() if request.data.get("revision_id") else e.revisiones.last()
        if revision is None:
            raise ValidationError("La revisión no existe en esta entrega.")
        c = ComentarioEntregaModel.objects.create(revision=revision, autor=request.user, texto=texto.strip())
        return respuesta_creada(datos={"id": str(c.id), "revision_id": str(revision.id), "autor_id": c.autor_id,
            "autor_nombre": request.user.nombre_completo or request.user.username, "texto": c.texto, "creado_en": c.creado_en})


class ReabrirEntregaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, id_entrega):
        if not es_docente(request.user):
            raise PermissionDenied()
        e = _entrega_visible(request.user, id_entrega)
        a = e.asignacion
        campo = serializers.DateTimeField(allow_null=True)
        if "fecha_limite" in request.data:
            a.fecha_limite = campo.run_validation(request.data["fecha_limite"])
        if a.fecha_limite and a.fecha_limite < timezone.now():
            raise ValidationError("Amplíe o quite el plazo vencido antes de reabrir.")
        if not a.curso.activo or a.estado != "VIGENTE":
            raise ValidationError("Reactive el curso y la asignación antes de reabrir.")
        a.save(update_fields=["fecha_limite"])
        e.estado = "BORRADOR"
        e.save(update_fields=["estado", "actualizada_en"])
        return respuesta_exitosa(datos=datos_entrega(e, incluir_contenido=False))
