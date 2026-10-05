from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0059_audit_request_id_accent_normalization'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asignacionip',
            name='ip',
            field=models.OneToOneField(
                on_delete=models.PROTECT,
                related_name='asignacion_activa',
                to='core.ip',
            ),
        ),
    ]
