"""Recalcula claves normalizadas sin tildes y añade correlación de auditoría."""

import unicodedata

from django.db import migrations, models


# Congelado para que migraciones futuras no dependan de cambios en models.py.
NORMALIZED_FIELDS = (
    ('Departamento', 'nombre', 'nombre_normalizado', False, None, False),
    ('SubArea', 'nombre', 'nombre_normalizado', False, None, True),
    ('Usuario', 'nombre_completo', 'nombre_completo_normalizado', False, None, False),
    ('Usuario', 'usuario_red', 'usuario_red_normalizado', False, None, False),
    ('Usuario', 'correo_corp', 'correo_corp_normalizado', False, None, False),
    ('Servidor', 'hostname', 'hostname_normalizado', False, None, False),
    ('Equipamiento', 'numero_serie', 'numero_serie_normalizado', True, None, False),
    ('Equipamiento', 'af', 'af_normalizado', True, None, False),
    ('Equipamiento', 'hostname', 'hostname_computador_normalizado', True, ('Notebook', 'Mac'), False),
    ('PerfilGenerico', 'usuario', 'usuario_normalizado', False, None, False),
    ('PCGenerico', 'hostname', 'hostname_normalizado', False, None, False),
    ('PCGenerico', 'numero_serie', 'numero_serie_normalizado', True, None, False),
    ('PCGenerico', 'activo_fijo', 'activo_fijo_normalizado', True, None, False),
)


def normalize_key(value):
    text = ' '.join(str(value or '').strip().split()).casefold()
    decomposed = unicodedata.normalize('NFKD', text)
    return ''.join(character for character in decomposed if not unicodedata.combining(character))


def normalized_value(instance, source, optional, allowed_types):
    enabled = not allowed_types or instance.tipo in allowed_types
    value = normalize_key(getattr(instance, source)) if enabled else ''
    return value or (None if optional else '')


def rebuild_normalized_keys(apps, schema_editor):
    alias = schema_editor.connection.alias

    # Validar todas las claves antes de cambiar alguna fila. La migración no
    # resuelve duplicados automáticamente porque podría mezclar identidades.
    for model_name, source, _target, optional, allowed_types, by_department in NORMALIZED_FIELDS:
        model = apps.get_model('core', model_name)
        fields = ['pk', source]
        if allowed_types:
            fields.append('tipo')
        if by_department:
            fields.append('departamento_id')

        seen = {}
        for instance in model.objects.using(alias).only(*fields).iterator(chunk_size=500):
            value = normalized_value(instance, source, optional, allowed_types)
            if value is None:
                continue
            key = (instance.departamento_id, value) if by_department else value
            previous_pk = seen.get(key)
            if previous_pk is not None:
                raise RuntimeError(
                    f'Colisión al normalizar {model_name}.{source}: '
                    f'registros {previous_pk} y {instance.pk}. '
                    'Resolverla antes de aplicar la migración.'
                )
            seen[key] = instance.pk

    for model_name, source, target, optional, allowed_types, _by_department in NORMALIZED_FIELDS:
        model = apps.get_model('core', model_name)
        fields = ['pk', source, target]
        if allowed_types:
            fields.append('tipo')
        pending = []
        for instance in model.objects.using(alias).only(*fields).iterator(chunk_size=500):
            value = normalized_value(instance, source, optional, allowed_types)
            if getattr(instance, target) != value:
                setattr(instance, target, value)
                pending.append(instance)
        if pending:
            model.objects.using(alias).bulk_update(pending, [target], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0058_volver_gestion_original_qr'),
    ]

    operations = [
        migrations.RunPython(rebuild_normalized_keys, migrations.RunPython.noop, atomic=True),
        migrations.AddField(
            model_name='securityauditlog',
            name='request_id',
            field=models.CharField(
                max_length=32, null=True, blank=True, db_index=True, editable=False,
            ),
        ),
    ]
