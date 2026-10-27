"""Gestión de cursos, invitaciones revocables y matrícula autenticada."""
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.actividades.models import AsignacionActividadModel, CursoModel, MatriculaCursoModel
from apps.actividades.models_cursos import generar_codigo_ingreso, generar_token_ingreso
from apps.permisos.codigos import Permisos
from compartido.respuestas.respuesta_api import respuesta_creada, respuesta_exitosa


def es_docente(usuario):
    return bool(usuario and usuario.is_authenticated and (
        usuario.is_superuser or usuario.groups.filter(name="Docente").exists()
        or usuario.has_perm(f"permisos.{Permisos.CURSOS_CREAR}")
    ))


def es_estudiante(usuario):
    return bool(usuario and usuario.is_authenticated and (
        usuario.groups.filter(name="Estudiante").exists()
        or usuario.has_perm(f"permisos.{Permisos.ACTIVIDADES_RESOLVER}")
    ))


def matricula_activa(curso, usuario):
    return bool(usuario and usuario.is_authenticated and MatriculaCursoModel.objects.filter(
        curso_id=getattr(curso, "id", curso), estudiante_id=usuario.id, activo=True,
    ).exists())


def curso_docente(usuario, id_curso):
    if not es_docente(usuario):
        raise PermissionDenied("Solo el docente del curso puede realizar esta acción.")
    cursos = CursoModel.objects.all()
    if not usuario.is_superuser:
        cursos = cursos.filter(docente_id=usuario.id)
    return get_object_or_404(cursos, pk=id_curso)


def curso_visible(usuario, id_curso):
    if es_docente(usuario):
        return curso_docente(usuario, id_curso)
    if not es_estudiante(usuario):
        raise PermissionDenied()
    return get_object_or_404(CursoModel.objects.filter(
        matriculas__estudiante_id=usuario.id, matriculas__activo=True,
    ), pk=id_curso)


def _datos_curso(curso, usuario, inscrito=None):
    propietario = usuario.is_superuser or curso.docente_id == usuario.id
    total = getattr(curso, "total_miembros", None)
    if total is None:
        total = curso.matriculas.filter(activo=True).count()
    datos = {
        "id": str(curso.id), "codigo": curso.codigo, "nombre": curso.nombre,
        "descripcion": curso.descripcion, "docente_id": curso.docente_id,
        "docente_nombre": getattr(curso.docente, "nombre_completo", "") or curso.docente.get_full_name() or curso.docente.username,
        "activo": curso.activo, "creado_en": curso.creado_en,
        "total_miembros": total,
        "matricula_activa": (matricula_activa(curso, usuario) if inscrito is None and not propietario else bool(inscrito)),
    }
    if propietario and es_docente(usuario):
        datos.update({
            "codigo_ingreso": curso.codigo_ingreso, "token_ingreso": curso.token_ingreso,
            "enlace_invitacion": f"/cursos/unirse?token={curso.token_ingreso}",
        })
    return datos


def _datos_miembro(matricula):
    estudiante = matricula.estudiante
    return {
        "id": str(matricula.id), "estudiante_id": estudiante.id,
        "estudiante_username": estudiante.username,
        "estudiante_nombre": getattr(estudiante, "nombre_completo", "") or estudiante.get_full_name() or estudiante.username,
        "estudiante_email": estudiante.email, "activo": matricula.activo,
        "fecha_ingreso": matricula.fecha_ingreso,
    }


class CursoCrearSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=50)
    nombre = serializers.CharField(max_length=150)
    descripcion = serializers.CharField(required=False, allow_null=True, allow_blank=True, default="")

    def validate_codigo(self, valor):
        return valor.strip().upper()


class CursoEditarSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=50, required=False)
    nombre = serializers.CharField(max_length=150, required=False)
    descripcion = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    activo = serializers.BooleanField(required=False)

    def validate_codigo(self, valor):
        return valor.strip().upper()


class UnirseCursoSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=50, required=False, allow_blank=False)
    token = serializers.CharField(max_length=128, required=False, allow_blank=False)

    def validate(self, datos):
        if bool(datos.get("codigo")) == bool(datos.get("token")):
            raise serializers.ValidationError("Indique el código de ingreso o el enlace de invitación.")
        return datos


class MiembroEditarSerializer(serializers.Serializer):
    activo = serializers.BooleanField(required=True)


class CursosListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario = request.user
        cursos = CursoModel.objects.select_related("docente").annotate(
            total_miembros=Count("matriculas", filter=Q(matriculas__activo=True), distinct=True),
        )
        if es_docente(usuario):
            if not usuario.is_superuser:
                cursos = cursos.filter(docente_id=usuario.id)
            inscrito = False
        elif es_estudiante(usuario):
            cursos = cursos.filter(matriculas__estudiante_id=usuario.id, matriculas__activo=True)
            inscrito = True
        else:
            raise PermissionDenied()
        datos = [_datos_curso(curso, usuario, inscrito=inscrito) for curso in cursos.order_by("nombre", "id")]
        return respuesta_exitosa(datos=datos)

    def post(self, request):
        if not es_docente(request.user):
            raise PermissionDenied()
        serializer = CursoCrearSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        if CursoModel.objects.filter(codigo__iexact=datos["codigo"]).exists():
            raise ValidationError({"codigo": "Ya existe un curso con este código académico."})
        if CursoModel.objects.filter(codigo_ingreso__iexact=datos["codigo"]).exists():
            raise ValidationError({"codigo": "El código académico no puede coincidir con una invitación."})
        try:
            with transaction.atomic():
                curso = CursoModel.objects.create(docente=request.user, **datos)
        except IntegrityError:
            raise ValidationError({"codigo": "Ya existe un curso con este código académico."})
        if CursoModel.objects.filter(codigo__iexact=curso.codigo_ingreso).exists():
            nuevo_codigo = generar_codigo_ingreso()
            while CursoModel.objects.filter(Q(codigo__iexact=nuevo_codigo) | Q(codigo_ingreso=nuevo_codigo)).exists():
                nuevo_codigo = generar_codigo_ingreso()
            curso.codigo_ingreso = nuevo_codigo
            curso.save(update_fields=["codigo_ingreso"])
        return respuesta_creada(datos=_datos_curso(curso, request.user))


class CursoDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        curso = curso_visible(request.user, id)
        datos = _datos_curso(curso, request.user)
        asignaciones = AsignacionActividadModel.objects.filter(curso=curso, actividad__activa=True).select_related("actividad")
        if not es_docente(request.user):
            asignaciones = asignaciones.filter(actividad__estado="PUBLICADA")
            asignaciones = asignaciones.exclude(actividad__sistema_experto__estado="BORRADOR")
        datos["asignaciones"] = [{
            "id": str(a.id), "actividad_id": str(a.actividad_id), "actividad_titulo": a.actividad.titulo,
            "curso_id": str(a.curso_id), "fecha_limite": a.fecha_limite, "estado": a.estado,
            "tipo": getattr(a.actividad, "tipo", "ANALISIS_BC"),
        } for a in asignaciones.order_by("-fecha_asignacion", "id")]
        return respuesta_exitosa(datos=datos)

    def patch(self, request, id):
        curso = curso_docente(request.user, id)
        serializer = CursoEditarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        if "codigo" in datos and CursoModel.objects.filter(codigo__iexact=datos["codigo"]).exclude(pk=curso.pk).exists():
            raise ValidationError({"codigo": "Ya existe un curso con este código académico."})
        if "codigo" in datos and CursoModel.objects.filter(codigo_ingreso__iexact=datos["codigo"]).exists():
            raise ValidationError({"codigo": "El código académico debe ser distinto del código de ingreso."})
        for campo, valor in datos.items():
            setattr(curso, campo, valor)
        try:
            with transaction.atomic():
                curso.save(update_fields=list(datos))
        except IntegrityError:
            raise ValidationError({"codigo": "Ya existe un curso con este código académico."})
        return respuesta_exitosa(datos=_datos_curso(curso, request.user))


class CursoUnirseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        if not es_estudiante(request.user):
            raise PermissionDenied("Solo una cuenta de estudiante puede matricularse.")
        serializer = UnirseCursoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        cursos = CursoModel.objects.select_for_update().filter(activo=True)
        curso = get_object_or_404(cursos, **(
            {"codigo_ingreso__iexact": datos["codigo"].strip()} if "codigo" in datos else {"token_ingreso": datos["token"]}
        ))
        matricula, creada = MatriculaCursoModel.objects.get_or_create(curso=curso, estudiante=request.user)
        if not matricula.activo:
            raise PermissionDenied("Su matrícula fue retirada. El docente debe reactivarla.")
        respuesta = _datos_curso(curso, request.user, inscrito=True)
        respuesta["matricula_id"] = str(matricula.id)
        return (respuesta_creada if creada else respuesta_exitosa)(datos=respuesta, mensaje="Matrícula activa.")


class CursoRegenerarInvitacionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, id):
        curso_docente(request.user, id)
        curso = CursoModel.objects.select_for_update().get(pk=id)
        codigo = generar_codigo_ingreso()
        while codigo == curso.codigo_ingreso or CursoModel.objects.filter(Q(codigo__iexact=codigo) | Q(codigo_ingreso=codigo)).exists():
            codigo = generar_codigo_ingreso()
        token = generar_token_ingreso()
        while token == curso.token_ingreso or CursoModel.objects.filter(token_ingreso=token).exists():
            token = generar_token_ingreso()
        curso.codigo_ingreso, curso.token_ingreso = codigo, token
        curso.save(update_fields=["codigo_ingreso", "token_ingreso"])
        return respuesta_exitosa(datos=_datos_curso(curso, request.user), mensaje="Invitación anterior revocada.")


class CursoMiembrosAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        curso = curso_docente(request.user, id)
        miembros = curso.matriculas.select_related("estudiante").all()
        return respuesta_exitosa(datos=[_datos_miembro(m) for m in miembros])


class CursoMiembroDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id, estudiante_id):
        curso = curso_docente(request.user, id)
        serializer = MiembroEditarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        matricula = get_object_or_404(curso.matriculas.select_related("estudiante"), estudiante_id=estudiante_id)
        matricula.activo = serializer.validated_data["activo"]
        matricula.save(update_fields=["activo"])
        return respuesta_exitosa(datos=_datos_miembro(matricula))
