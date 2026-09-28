import hashlib
import json
from datetime import date, datetime, timezone as datetime_timezone
from pathlib import Path
from uuid import UUID

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


SNAPSHOT_VERSION = 1
EXCLUDED_CORE_MODELS = {'portalsession'}


def _normalize_value(value):
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(datetime_timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def _hash_rows(rows):
    digest = hashlib.sha256()
    count = 0
    for row in rows:
        payload = [_normalize_value(value) for value in row]
        digest.update(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(',', ':'),
                default=str,
            ).encode('utf-8')
        )
        digest.update(b'\n')
        count += 1
    return count, digest.hexdigest()


def _model_snapshot(model):
    field_names = [field.attname for field in model._meta.concrete_fields]
    pk_name = model._meta.pk.attname
    rows = (
        model._default_manager.order_by(pk_name)
        .values_list(*field_names)
        .iterator(chunk_size=1000)
    )
    count, fingerprint = _hash_rows(rows)
    return {
        'table': model._meta.db_table,
        'count': count,
        'sha256': fingerprint,
    }


def _through_snapshot(name, model, owner_field, related_field):
    rows = (
        model._default_manager.order_by(owner_field, related_field)
        .values_list(owner_field, related_field)
        .iterator(chunk_size=1000)
    )
    count, fingerprint = _hash_rows(rows)
    return name, {
        'table': model._meta.db_table,
        'count': count,
        'sha256': fingerprint,
    }


def build_snapshot():
    core_models = [
        model
        for model in apps.get_app_config('core').get_models()
        if model._meta.model_name not in EXCLUDED_CORE_MODELS
    ]
    auth_models = [
        apps.get_model('auth', 'User'),
        apps.get_model('auth', 'Group'),
    ]

    models = {}
    for model in sorted(
        [*core_models, *auth_models],
        key=lambda item: item._meta.label_lower,
    ):
        models[model._meta.label_lower] = _model_snapshot(model)

    user_model = apps.get_model('auth', 'User')
    group_model = apps.get_model('auth', 'Group')
    relations = dict([
        _through_snapshot(
            'auth.user_groups',
            user_model.groups.through,
            'user_id',
            'group_id',
        ),
        _through_snapshot(
            'auth.user_user_permissions',
            user_model.user_permissions.through,
            'user_id',
            'permission_id',
        ),
        _through_snapshot(
            'auth.group_permissions',
            group_model.permissions.through,
            'group_id',
            'permission_id',
        ),
    ])

    applied_migrations = sorted(
        f'{app_label}.{name}'
        for app_label, name in MigrationRecorder(connection).applied_migrations()
        if app_label in {'core', 'auth', 'contenttypes'}
    )

    return {
        'snapshot_version': SNAPSHOT_VERSION,
        'generated_at_utc': datetime.now(datetime_timezone.utc).isoformat(),
        'database': {
            'vendor': connection.vendor,
            'name': Path(str(connection.settings_dict['NAME'])).name,
        },
        'models': models,
        'relations': relations,
        'applied_migrations': applied_migrations,
        'excluded_transient_data': [
            'core.portalsession',
            'sessions.session',
            'token_blacklist.*',
        ],
    }


def _comparison_payload(snapshot):
    return {
        'snapshot_version': snapshot.get('snapshot_version'),
        'models': snapshot.get('models'),
        'relations': snapshot.get('relations'),
        'applied_migrations': snapshot.get('applied_migrations'),
        'excluded_transient_data': snapshot.get('excluded_transient_data'),
    }


class Command(BaseCommand):
    help = (
        'Genera conteos y huellas SHA-256 para validar una migración entre '
        'SQLite y MySQL sin exponer los datos.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--salida',
            help='Ruta del archivo JSON que recibirá la auditoría.',
        )
        parser.add_argument(
            '--comparar',
            help='Auditoría JSON anterior que debe coincidir con la base actual.',
        )

    def handle(self, *args, **options):
        snapshot = build_snapshot()
        serialized = json.dumps(snapshot, ensure_ascii=False, indent=2)

        output_path = options.get('salida')
        if output_path:
            path = Path(output_path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(serialized + '\n', encoding='utf-8')
            self.stdout.write(f'Auditoría guardada en: {path}')
        elif not options.get('comparar'):
            self.stdout.write(serialized)

        comparison_path = options.get('comparar')
        if not comparison_path:
            return

        path = Path(comparison_path).resolve()
        if not path.exists():
            raise CommandError(f'No existe la auditoría a comparar: {path}')

        try:
            expected = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(
                f'No fue posible leer la auditoría a comparar: {exc}'
            ) from exc

        if _comparison_payload(expected) != _comparison_payload(snapshot):
            raise CommandError(
                'La base actual no coincide con la auditoría de origen. '
                'Revisa conteos, huellas y migraciones antes de habilitar el portal.'
            )

        self.stdout.write(
            self.style.SUCCESS(
                'La base actual coincide con la auditoría de origen.'
            )
        )
