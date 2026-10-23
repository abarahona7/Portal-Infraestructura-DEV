from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.crypto import needs_rotation, rotate_value
from core.management.commands.verify_secrets import TARGETS


class Command(BaseCommand):
    help = 'Verifica o rota secretos hacia la primera clave de FIELD_ENCRYPTION_KEYS.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplica la rotación. Sin esta opción solo simula y verifica.',
        )
        parser.add_argument(
            '--confirm',
            default='',
            help='Para aplicar debe indicar ROTATE_ENCRYPTION_KEYS.',
        )

    def handle(self, *args, **options):
        if options['apply'] and options['confirm'] != 'ROTATE_ENCRYPTION_KEYS':
            raise CommandError(
                'Para aplicar usa --apply --confirm ROTATE_ENCRYPTION_KEYS después del respaldo.'
            )

        pending = 0
        invalid = []
        with transaction.atomic():
            for model, fields in TARGETS:
                manager = getattr(model, 'all_objects', model.objects)
                for row in manager.values_list('pk', *fields).iterator(chunk_size=500):
                    pk, *values = row
                    updates = {}
                    for field, value in zip(fields, values):
                        if not value:
                            continue
                        try:
                            must_rotate = needs_rotation(value)
                        except (RuntimeError, ValueError, UnicodeError, TypeError):
                            invalid.append(f'{model.__name__}:{pk}:{field}')
                            continue
                        if must_rotate:
                            pending += 1
                            if options['apply']:
                                updates[field] = rotate_value(value)
                    if updates:
                        manager.filter(pk=pk).update(**updates)
            if invalid:
                transaction.set_rollback(True)
                for reference in invalid[:50]:
                    self.stdout.write(reference)
                raise CommandError(
                    f'Rotación cancelada: {len(invalid)} secreto(s) no se pudieron descifrar.'
                )
            if not options['apply']:
                transaction.set_rollback(True)

        action = 'rotados' if options['apply'] else 'por rotar'
        self.stdout.write(self.style.SUCCESS(f'Secretos {action}: {pending}'))
