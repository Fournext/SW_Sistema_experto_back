from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inferencia", "0005_ejecucion_recorrido_por_regla")]

    operations = [
        migrations.AddField(
            model_name="detalleinferenciamodel",
            name="paso_visual",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
