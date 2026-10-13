from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0062_historialasignacionip_observacion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='papeleraevento',
            name='contexto',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
