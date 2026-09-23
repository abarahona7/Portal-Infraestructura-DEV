"""Importador v1.1 con previsualización sin escrituras y carga atómica."""

import hmac
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.crypto import encrypt_val
from core.models import (
    Anexo, Departamento, Equipamiento, IP, PCGenerico, PerfilGenerico, Usuario,
)
from core.services.importacion_v11 import FILES, file_digest, make_plan


class Command(BaseCommand):
    help = 'Previsualiza o importa los cinco Excel v1.1 sin sobrescribir registros existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--input-dir', required=True, type=Path)
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument('--dry-run', action='store_true')
        mode.add_argument('--apply', action='store_true')
        parser.add_argument('--expected-sha256', help='SHA-256 del reporte dry-run aprobado')
        parser.add_argument('--report', type=Path)

    def handle(self, *args, **options):
        root = options['input_dir']
        missing = [filename for filename in FILES.values() if not (root / filename).is_file()]
        if missing:
            raise CommandError('Faltan archivos: ' + ', '.join(missing))
        digest = file_digest(root)
        if options['apply']:
            expected = options['expected_sha256']
            if not expected or not hmac.compare_digest(expected, digest):
                raise CommandError('El SHA-256 no coincide con el dry-run aprobado.')
            if not settings.FIELD_ENCRYPTION_KEY:
                raise CommandError('FIELD_ENCRYPTION_KEY es obligatoria para importar secretos.')
            try:
                encrypt_val('verificacion_de_clave')
            except (RuntimeError, ValueError) as exc:
                raise CommandError('FIELD_ENCRYPTION_KEY no es una clave Fernet válida.') from exc

        try:
            if options['apply']:
                with transaction.atomic():
                    plan = make_plan(root)
                    self.apply_plan(plan)
            else:
                plan = make_plan(root)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        result = plan.public_report(digest)
        result['mode'] = 'apply' if options['apply'] else 'dry-run'
        result['database_writes'] = sum(result['planned'].values()) if options['apply'] else 0
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if options['report']:
            destination = options['report'].resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(payload + '\n', encoding='utf-8')
            self.stdout.write(f'Reporte: {destination}')
        self.stdout.write('SHA-256: ' + digest)
        self.stdout.write(json.dumps(result['planned'], ensure_ascii=False, sort_keys=True))
        self.stdout.write(f'Observaciones: {len(result["issues"])}')
        self.stdout.write('No se modificó la base de datos.' if options['dry_run'] else 'Importación atómica completada.')

    def apply_plan(self, plan):
        departments = {}
        new_users = {}
        current_module = 'departamentos'
        current_row = 0
        try:
            for identity, item in plan.departments.items():
                if item['new']:
                    department = Departamento(nombre=item['name'])
                    department.full_clean()
                    department.save()
                else:
                    department = Departamento.objects.get(pk=item['id'])
                departments[identity] = department

            current_module = 'usuarios'
            for item in plan.users:
                current_row = item['row']
                user = Usuario(departamento=departments[item['department']], **item['data'])
                user.full_clean()
                user.save()
                new_users[current_row] = user

            def resolve_user(reference):
                if reference is None:
                    return None
                return (Usuario.objects.get(pk=reference[1]) if reference[0] == 'db'
                        else new_users[reference[1]])

            current_module = 'equipos'
            for item in plan.equipment:
                current_row = item['row']
                equipment = Equipamiento(usuario=resolve_user(item['user']), **item['data'])
                equipment.full_clean()
                equipment.save()

            current_module = 'ips'
            for item in plan.ips:
                current_row = item['row']
                ip = IP(direccion_ip=item['ip'], estado='LIBRE')
                ip.full_clean()
                ip.save()

            current_module = 'anexos'
            for item in plan.annexes:
                current_row = item['row']
                annex = Anexo(usuario=resolve_user(item['user']), **item['data'])
                annex.full_clean()
                annex.save()

            current_module = 'perfiles'
            for item in plan.profiles:
                current_row = item['row']
                profile = PerfilGenerico(departamento=departments[item['department']], **item['data'])
                profile.full_clean()
                profile.save()

            current_module = 'pcs'
            for item in plan.pcs:
                current_row = item['row']
                pc = PCGenerico(**item['data'])
                pc.full_clean()
                pc.save()
        except Exception as exc:
            raise CommandError(
                f'Importación revertida; módulo {current_module}, fila {current_row}; '
                f'error {type(exc).__name__}. No se imprimen valores sensibles.'
            ) from None
