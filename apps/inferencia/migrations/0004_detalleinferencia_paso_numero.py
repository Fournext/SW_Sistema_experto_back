from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inferencia", "0003_detalleinferencia_condiciones_evaluadas"),
    ]

    operations = [
        migrations.AddField(
            model_name="detalleinferenciamodel",
            name="paso_numero",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
