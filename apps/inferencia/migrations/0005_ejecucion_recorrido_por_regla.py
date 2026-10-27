from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inferencia", "0004_detalleinferencia_paso_numero")]

    operations = [
        migrations.AddField(
            model_name="ejecucioninferenciamodel",
            name="recorrido_por_regla",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
