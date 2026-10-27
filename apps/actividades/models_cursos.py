"""Matrículas e invitaciones de cursos; no se matriculan estudiantes históricos."""
import secrets
import uuid

from django.conf import settings
from django.db import models


def generar_codigo_ingreso():
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(10))


def generar_token_ingreso():
    return secrets.token_urlsafe(32)


class MatriculaCursoModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    curso = models.ForeignKey("actividades.CursoModel", on_delete=models.CASCADE, related_name="matriculas")
    estudiante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="matriculas_cursos")
    activo = models.BooleanField(default=True)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "matriculas_cursos"
        ordering = ["fecha_ingreso", "id"]
        constraints = [models.UniqueConstraint(fields=["curso", "estudiante"], name="unique_matricula_curso_estudiante")]
