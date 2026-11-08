from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('actividades', '0004_seleccion_ejecuciones'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='entregaactividadmodel',
            name='calificacion',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                verbose_name='Calificación / Nota obtenida',
            ),
        ),
        migrations.AddField(
            model_name='entregaactividadmodel',
            name='calificada_en',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Fecha de calificación',
            ),
        ),
        migrations.AddField(
            model_name='entregaactividadmodel',
            name='calificada_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='entregas_calificadas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Docente que calificó',
            ),
        ),
        migrations.AddConstraint(
            model_name='entregaactividadmodel',
            constraint=models.CheckConstraint(
                condition=models.Q(calificacion__isnull=True)
                | (models.Q(calificacion__gte=0) & models.Q(calificacion__lte=100)),
                name='chk_entrega_calificacion_rango',
            ),
        ),
    ]
