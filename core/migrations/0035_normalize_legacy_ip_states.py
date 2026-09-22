from django.db import migrations


def normalize_ip_states(apps, schema_editor):
    IP = apps.get_model('core', 'IP')
    # Los estados históricos que ya no forman parte del modelo se conservan
    # como no disponibles para uso, por lo que se normalizan a RESERVADA.
    IP.objects.filter(
        estado__in=['ASIGNADA', 'DUPLICADA', 'DESCONOCIDA']
    ).update(estado='RESERVADA')


def reverse_normalize_ip_states(apps, schema_editor):
    # No existe una forma segura de reconstruir el estado histórico exacto.
    # La reversa se deja intencionalmente como no-op.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_alter_ip_estado'),
    ]

    operations = [
        migrations.RunPython(
            normalize_ip_states,
            reverse_normalize_ip_states,
        ),
    ]
