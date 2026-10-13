"""Consulta y gestiona retiros excepcionales fuera de la API del portal."""

import json
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError

from core.audit import reset_current_audit_user, set_current_audit_user
from core.models import PapeleraEvento
from core.services.papelera import (
    ARCHIVABLE_MODELS, archive_record, build_archive_impact,
    impact_fingerprint, restore_record,
)


class Command(BaseCommand):
    help = 'Inspecciona, archiva, restaura o exporta registros con control técnico.'

    def add_arguments(self, parser):
        parser.add_argument('accion', choices=('inspeccionar', 'archivar', 'restaurar', 'reporte'))
        parser.add_argument('modulo', nargs='?')
        parser.add_argument('registro_id', nargs='?', type=int)
        parser.add_argument('--actor', required=True, help='Usuario Django superusuario responsable.')
        parser.add_argument('--motivo', help='Motivo o identificador de la solicitud.')
        parser.add_argument('--huella', help='Huella obtenida con inspeccionar.')
        parser.add_argument('--confirmar', help='ARCHIVAR:modulo:id o RESTAURAR:modulo:id.')
        parser.add_argument('--salida', help='Ruta nueva para el reporte JSON (modo 0600).')

    def handle(self, *args, **options):
        actor = get_user_model().objects.filter(username=options['actor'], is_active=True,
                                                is_superuser=True).first()
        if actor is None:
            raise CommandError('El actor debe ser un superusuario activo de Django.')

        action = options['accion']
        module = options['modulo']
        record_id = options['registro_id']
        if action == 'reporte':
            if record_id is not None or (module and module not in ARCHIVABLE_MODELS):
                raise CommandError('Para reporte, usa un módulo válido opcional y sin ID.')
            self._report(module, options['salida'])
            return
        if module not in ARCHIVABLE_MODELS or not record_id or record_id < 1:
            raise CommandError('Indica un módulo válido y un ID positivo.')

        model = ARCHIVABLE_MODELS[module]
        instance = model.all_objects.filter(pk=record_id).first()
        if instance is None:
            raise CommandError('Registro no encontrado.')

        if action == 'inspeccionar':
            impact = (instance.archive_context.get('impacto') or {}
                      if instance.deleted_at else build_archive_impact(instance))
            self.stdout.write(json.dumps({
                'archivado': bool(instance.deleted_at),
                'impacto': impact,
                'huella': impact_fingerprint(impact) if impact else None,
                'contexto_archivo': instance.archive_context if instance.deleted_at else None,
            }, ensure_ascii=False, indent=2, default=str))
            return

        reason = (options['motivo'] or '').strip()
        if not reason:
            raise CommandError('Debes indicar --motivo con la solicitud o explicación.')
        expected_confirmation = f'{action.upper()}:{module}:{record_id}'
        if options['confirmar'] != expected_confirmation:
            raise CommandError(f'Confirma la operación con --confirmar {expected_confirmation}.')
        if action == 'archivar' and not options['huella']:
            raise CommandError('Inspecciona el registro y pasa la huella con --huella.')

        token = set_current_audit_user(actor)
        try:
            if action == 'archivar':
                if instance.deleted_at:
                    raise CommandError('El registro ya está archivado.')
                archive_record(instance, reason=reason,
                               expected_fingerprint=options['huella'])
            else:
                if not instance.deleted_at:
                    raise CommandError('El registro no está archivado.')
                restore_record(module, record_id, reason=reason)
        except ValidationError as exc:
            raise CommandError(str(exc.detail)) from exc
        finally:
            reset_current_audit_user(token)
        self.stdout.write(self.style.SUCCESS(
            f'{module} #{record_id}: {"archivado" if action == "archivar" else "restaurado"}. '
            'Las asignaciones liberadas se revisan manualmente.'
        ))

    def _report(self, module, output_path):
        if not output_path:
            raise CommandError('El reporte requiere --salida con una ruta nueva.')
        modules = [module] if module else ARCHIVABLE_MODELS
        archived = []
        for name in modules:
            for instance in ARCHIVABLE_MODELS[name].all_objects.filter(
                    deleted_at__isnull=False).order_by('pk'):
                archived.append({
                    'modulo': name,
                    'id': instance.pk,
                    'nombre': str(instance),
                    'fecha_archivo': instance.deleted_at.isoformat(),
                    'archivado_por': instance.deleted_by,
                    'contexto': instance.archive_context,
                })
        events = list(PapeleraEvento.objects.filter(
            **({'modulo': module} if module else {})
        ).order_by('pk').values('modulo', 'registro_id', 'accion', 'realizado_por',
                                 'fecha', 'detalle', 'contexto'))
        data = json.dumps({'archivados': archived, 'eventos': events},
                          ensure_ascii=False, indent=2, default=str)
        try:
            descriptor = os.open(output_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as report:
                report.write(data + '\n')
        except OSError as exc:
            raise CommandError(f'No se pudo crear el reporte: {exc}') from exc
        self.stdout.write(self.style.SUCCESS(
            f'Reporte creado en {output_path}: {len(archived)} archivados y {len(events)} eventos.'
        ))
