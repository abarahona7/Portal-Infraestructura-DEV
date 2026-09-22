from django.db import migrations, models
import django.db.models.deletion


def _normalize_spaces(value):
    if value is None:
        return ''
    return ' '.join(str(value).strip().split())


def _normalize_key(value):
    return _normalize_spaces(value).casefold()


def migrate_perfiles(apps, schema_editor):
    PerfilGenerico = apps.get_model('core', 'PerfilGenerico')
    Departamento = apps.get_model('core', 'Departamento')
    SubArea = apps.get_model('core', 'SubArea')

    departamentos = {
        departamento.nombre_normalizado: departamento
        for departamento in Departamento.objects.all()
    }

    subareas_by_name = {}
    for subarea in SubArea.objects.select_related('departamento').all():
        key = subarea.nombre_normalizado
        subareas_by_name.setdefault(key, []).append(subarea)

    for perfil in PerfilGenerico.objects.all().iterator():
        updates = {}

        if perfil.estado != 'ACTIVO':
            updates['estado'] = 'INACTIVO'

        legacy_name = _normalize_spaces(perfil.dpto_area)
        if legacy_name and not perfil.departamento_id:
            normalized = _normalize_key(legacy_name)
            departamento = departamentos.get(normalized)
            subarea = None

            if departamento is None:
                matches = subareas_by_name.get(normalized, [])
                if len(matches) == 1:
                    subarea = matches[0]
                    departamento = subarea.departamento

            if departamento is None:
                departamento, _ = Departamento.objects.get_or_create(
                    nombre_normalizado=normalized,
                    defaults={
                        'nombre': legacy_name,
                        'activo': True,
                    },
                )
                departamentos[normalized] = departamento

            updates['departamento_id'] = departamento.pk
            if subarea is not None:
                updates['subarea_id'] = subarea.pk
                updates['dpto_area'] = subarea.nombre
            else:
                updates['dpto_area'] = departamento.nombre

        if updates:
            PerfilGenerico.objects.filter(pk=perfil.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_departamentos_subareas'),
    ]

    operations = [
        migrations.AlterField(
            model_name='perfilgenerico',
            name='dpto_area',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='perfilgenerico',
            name='departamento',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='perfiles_genericos',
                to='core.departamento',
            ),
        ),
        migrations.AddField(
            model_name='perfilgenerico',
            name='subarea',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='perfiles_genericos',
                to='core.subarea',
            ),
        ),
        migrations.AlterField(
            model_name='perfilgenerico',
            name='estado',
            field=models.CharField(
                choices=[('ACTIVO', 'Activo'), ('INACTIVO', 'Inactivo')],
                default='ACTIVO',
                max_length=20,
            ),
        ),
        migrations.RunPython(
            migrate_perfiles,
            migrations.RunPython.noop,
        ),
    ]
