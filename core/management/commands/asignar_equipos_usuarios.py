"""Asigna equipos existentes desde el Excel conciliado de usuarios."""

import hmac
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.audit import reset_current_audit_user, set_current_audit_user
from core.models import Equipamiento, Usuario
from core.serializers import EquipamientoSerializer
from core.services.asignacion_equipos import build_plan, source_digest, write_pending_report


class _ImportAuditUser:
    is_authenticated = True

    @staticmethod
    def get_username():
        return 'importacion_equipos_v11'


class Command(BaseCommand):
    help = 'Previsualiza o aplica asignaciones exactas de equipos existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--source', required=True, type=Path)
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument('--dry-run', action='store_true')
        mode.add_argument('--apply', action='store_true')
        parser.add_argument('--expected-sha256')
        parser.add_argument('--pending-report', required=True, type=Path)

    def handle(self, *args, **options):
        source = options['source'].resolve()
        if not source.is_file():
            raise CommandError(f'No existe el archivo origen: {source}')

        digest = source_digest(source)
        if options['apply'] and (
            not options['expected_sha256']
            or not hmac.compare_digest(options['expected_sha256'], digest)
        ):
            raise CommandError('El SHA-256 no coincide con la previsualización aprobada.')

        plan = build_plan(source)
        report = options['pending_report'].resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        write_pending_report(report, plan, digest)

        if options['apply']:
            token = set_current_audit_user(_ImportAuditUser())
            try:
                with transaction.atomic():
                    for assignment in plan['safe']:
                        equipment = Equipamiento.objects.select_for_update().get(
                            pk=assignment['equipment_id'],
                            usuario__isnull=True,
                        )
                        user = Usuario.objects.get(pk=assignment['user_id'])
                        payload = {'usuario': user.pk}
                        if assignment['assignment_date']:
                            payload['fecha_asignacion'] = assignment['assignment_date']
                        serializer = EquipamientoSerializer(
                            equipment,
                            data=payload,
                            partial=True,
                        )
                        serializer.is_valid(raise_exception=True)
                        serializer.save()
            except (Equipamiento.DoesNotExist, Usuario.DoesNotExist, ValidationError) as exc:
                raise CommandError(
                    'La asignación fue revertida porque los datos cambiaron o una '
                    f'validación falló ({type(exc).__name__}).'
                ) from None
            finally:
                reset_current_audit_user(token)

        result = {
            'mode': 'apply' if options['apply'] else 'dry-run',
            'source_sha256': digest,
            'safe_assignments': len(plan['safe']),
            'pending_existing_equipment': len(plan['pending']),
            'spreadsheet_candidates_without_existing_equipment': plan['unmatched_candidates'],
            'database_writes': len(plan['safe']) if options['apply'] else 0,
            'pending_report': str(report),
        }
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        if options['apply']:
            self.stdout.write(self.style.SUCCESS('Asignación atómica completada.'))
        else:
            self.stdout.write('Previsualización completada. No se modificó la base de datos.')
