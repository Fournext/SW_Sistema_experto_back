import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models

from apps.actividades.models_cursos import generar_codigo_ingreso, generar_token_ingreso


def preparar_invitaciones(apps, schema_editor):
    Curso = apps.get_model("actividades", "CursoModel")
    for curso in Curso.objects.all().iterator():
        codigo = generar_codigo_ingreso()
        while Curso.objects.filter(codigo__iexact=codigo).exists() or Curso.objects.filter(codigo_ingreso=codigo).exists():
            codigo = generar_codigo_ingreso()
        token = generar_token_ingreso()
        while Curso.objects.filter(token_ingreso=token).exists():
            token = generar_token_ingreso()
        Curso.objects.filter(pk=curso.pk).update(codigo_ingreso=codigo, token_ingreso=token)


class Migration(migrations.Migration):
    dependencies = [("actividades", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="cursomodel", name="codigo_ingreso",
                            field=models.CharField(max_length=20, unique=True, null=True, editable=False)),
        migrations.AddField(model_name="cursomodel", name="token_ingreso",
                            field=models.CharField(max_length=128, unique=True, null=True, editable=False)),
        migrations.RunPython(preparar_invitaciones, migrations.RunPython.noop),
        migrations.AlterField(model_name="cursomodel", name="codigo_ingreso",
                              field=models.CharField(max_length=20, unique=True, default=generar_codigo_ingreso, editable=False)),
        migrations.AlterField(model_name="cursomodel", name="token_ingreso",
                              field=models.CharField(max_length=128, unique=True, default=generar_token_ingreso, editable=False)),
        migrations.CreateModel(
            name="MatriculaCursoModel",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("activo", models.BooleanField(default=True)),
                ("fecha_ingreso", models.DateTimeField(auto_now_add=True)),
                ("curso", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="matriculas", to="actividades.cursomodel")),
                ("estudiante", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="matriculas_cursos", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "matriculas_cursos", "ordering": ["fecha_ingreso", "id"]},
        ),
        migrations.AddConstraint(model_name="matriculacursomodel",
                                constraint=models.UniqueConstraint(fields=("curso", "estudiante"), name="unique_matricula_curso_estudiante")),
    ]
