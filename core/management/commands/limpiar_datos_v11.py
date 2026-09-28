"""Limpia los datos del portal antes de la importación v1.1 con respaldo SQLite."""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core.models import (
    Anexo, AsignacionIP, Departamento, Equipamiento, HistorialAnexo,
    HistorialAsignacionIP, HistorialEquipo, HistorialPCGenerico,
    HistorialPerfilGenerico, HistorialServidor, HistorialUsuario, IP,
    PCGenerico, PerfilGenerico, PortalSession, SecurityAuditLog, Servidor,
    SubArea, Usuario,
)


DELETE_ORDER = (
    PortalSession, AsignacionIP, Anexo, Equipamiento, Servidor,
    PerfilGenerico, PCGenerico, Usuario, IP, HistorialAnexo,
    HistorialAsignacionIP, HistorialEquipo, HistorialPCGenerico,
    HistorialPerfilGenerico, HistorialServidor, HistorialUsuario,
    SecurityAuditLog, SubArea, Departamento,
)


class Command(BaseCommand):
    help = 'Respalda SQLite y borra solo los datos de core; conserva cuentas y roles.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--expected-db-path', type=Path)
        parser.add_argument('--report', type=Path)

    def handle(self, *args, **options):
        engine = connection.settings_dict['ENGINE']
        if engine != 'django.db.backends.sqlite3':
            raise CommandError('Esta limpieza exige SQLite para realizar un respaldo verificable.')
        database = Path(connection.settings_dict['NAME']).resolve()
        if not database.is_file():
            raise CommandError('No existe la base SQLite configurada.')
        configured_models = set(apps.get_app_config('core').get_models())
        if configured_models != set(DELETE_ORDER):
            raise CommandError('La lista de modelos core cambió; revisar antes de borrar.')
        counts = {model.__name__: model.objects.count() for model in DELETE_ORDER}
        self.stdout.write('Base: ' + str(database))
        self.stdout.write(json.dumps(counts, sort_keys=True))
        if not options['apply']:
            self.stdout.write('Vista previa: no se modificó la base de datos.')
            return

        expected = options['expected_db_path']
        if expected is None or expected.resolve() != database:
            raise CommandError('--expected-db-path debe coincidir con la base configurada.')
        backup = database.with_name(
            f'{database.stem}_antes_import_v11_{datetime.now():%Y%m%d_%H%M%S_%f}.sqlite3'
        )
        if backup.exists():
            raise CommandError('El respaldo ya existe; no se sobrescribirá.')

        with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
            source.backup(target)
            integrity = target.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise CommandError('Falló la verificación del respaldo; no se borró ningún dato.')
        with backup.open('rb') as backup_file:
            digest = hashlib.file_digest(backup_file, 'sha256').hexdigest()

        with transaction.atomic():
            for model in DELETE_ORDER:
                model.objects.all().delete()
            remaining = {model.__name__: model.objects.count() for model in DELETE_ORDER}
            if any(remaining.values()):
                raise CommandError('La limpieza no terminó; la transacción se revertirá.')

        report = {
            'database': str(database), 'backup': str(backup),
            'backup_sha256': digest, 'deleted_counts': counts,
            'remaining_counts': remaining,
            'auth_users_and_groups_preserved': True,
        }
        if options['report']:
            destination = options['report'].resolve()
            destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            self.stdout.write('Reporte: ' + str(destination))
        self.stdout.write('Respaldo: ' + str(backup))
        self.stdout.write('Limpieza completada. Cuentas y roles conservados.')
