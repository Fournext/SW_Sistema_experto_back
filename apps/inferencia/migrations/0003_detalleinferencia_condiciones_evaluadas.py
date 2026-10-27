from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inferencia", "0002_ejecucioninferenciamodel_es_simulacion_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="detalleinferenciamodel",
            name="condiciones_evaluadas",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
