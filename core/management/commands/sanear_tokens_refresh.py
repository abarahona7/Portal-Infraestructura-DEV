from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from core.token_storage import REDACTED_TOKEN_PREFIX


class Command(BaseCommand):
    help = 'Reemplaza JWT refresh persistidos por una marca no reutilizable. Simula por defecto.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplica la sanitización. Sin esta opción no modifica la base.',
        )

    def handle(self, *args, **options):
        queryset = OutstandingToken.objects.exclude(token__startswith=REDACTED_TOKEN_PREFIX)
        pending = queryset.count()
        if not options['apply']:
            self.stdout.write(
                f'Simulación: {pending} token(s) quedarían sanitizados. '
                'Ejecuta nuevamente con --apply después del respaldo y la revisión.'
            )
            return

        with transaction.atomic():
            updated = 0
            for token in queryset.only('pk', 'jti').iterator():
                updated += OutstandingToken.objects.filter(pk=token.pk).update(
                    token=f'{REDACTED_TOKEN_PREFIX}{token.jti}'
                )
        self.stdout.write(self.style.SUCCESS(f'{updated} token(s) sanitizados.'))

