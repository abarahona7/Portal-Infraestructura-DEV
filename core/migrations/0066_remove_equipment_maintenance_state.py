from django.db import migrations, models


def normalize_maintenance_state(apps, schema_editor):
    equipment = apps.get_model('core', 'Equipamiento')
    equipment._base_manager.filter(
        estado='MANTENCION',
        usuario_id__isnull=False,
    ).update(estado='ASIGNADO')
    equipment._base_manager.filter(
        estado='MANTENCION',
        usuario_id__isnull=True,
    ).update(estado='STOCK')


class Migration(migrations.Migration):
    dependencies = [('core', '0065_revisionbajausuario_motivo')]

    operations = [
        migrations.RemoveConstraint(
            model_name='equipamiento',
            name='ck_equipo_asignacion_valida',
        ),
        migrations.RunPython(
            normalize_maintenance_state,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='equipamiento',
            name='estado',
            field=models.CharField(
                choices=[
                    ('ASIGNADO', 'Asignado'),
                    ('STOCK', 'Stock / Disponible'),
                    ('BAJA', 'Dado de Baja'),
                ],
                default='ASIGNADO',
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name='equipamiento',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        usuario__isnull=True,
                        fecha_asignacion__isnull=True,
                        estado__in=['STOCK', 'BAJA'],
                    )
                    | models.Q(
                        usuario__isnull=False,
                        estado__in=['ASIGNADO', 'BAJA'],
                    )
                ),
                name='ck_equipo_asignacion_valida',
            ),
        ),
    ]
