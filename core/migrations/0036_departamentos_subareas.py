from django.db import migrations, models
import django.db.models.deletion


def _normalize_spaces(value):
    if value is None:
        return ''
    return ' '.join(str(value).strip().split())


def _normalize_key(value):
    return _normalize_spaces(value).casefold()


def migrate_legacy_departments(apps, schema_editor):
    Usuario = apps.get_model('core', 'Usuario')
    Departamento = apps.get_model('core', 'Departamento')

    cache = {}

    for usuario in Usuario.objects.all().iterator():
        legacy_name = _normalize_spaces(usuario.dpto_area)
        if not legacy_name:
            continue

        normalized = _normalize_key(legacy_name)
        departamento = cache.get(normalized)

        if departamento is None:
            departamento, _ = Departamento.objects.get_or_create(
                nombre_normalizado=normalized,
                defaults={
                    'nombre': legacy_name,
                    'activo': True,
                },
            )
            cache[normalized] = departamento

        Usuario.objects.filter(pk=usuario.pk).update(
            departamento_id=departamento.pk,
            dpto_area=departamento.nombre,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_normalize_legacy_ip_states'),
    ]

    operations = [
        migrations.CreateModel(
            name='Departamento',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('nombre', models.CharField(max_length=100)),
                (
                    'nombre_normalizado',
                    models.CharField(
                        editable=False,
                        max_length=100,
                        unique=True,
                    ),
                ),
                ('activo', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Departamento',
                'verbose_name_plural': 'Departamentos',
                'ordering': ['nombre'],
            },
        ),
        migrations.CreateModel(
            name='SubArea',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('nombre', models.CharField(max_length=100)),
                (
                    'nombre_normalizado',
                    models.CharField(editable=False, max_length=100),
                ),
                ('activo', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                (
                    'departamento',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='subareas',
                        to='core.departamento',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Subárea',
                'verbose_name_plural': 'Subáreas',
                'ordering': ['departamento__nombre', 'nombre'],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('departamento', 'nombre_normalizado'),
                        name='uniq_subarea_departamento_nombre_norm',
                    ),
                ],
            },
        ),
        migrations.AlterField(
            model_name='usuario',
            name='dpto_area',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='usuario',
            name='departamento',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='usuarios',
                to='core.departamento',
            ),
        ),
        migrations.AddField(
            model_name='usuario',
            name='subarea',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='usuarios',
                to='core.subarea',
            ),
        ),
        migrations.RunPython(
            migrate_legacy_departments,
            migrations.RunPython.noop,
        ),
    ]
