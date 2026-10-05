from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.crypto import ENC_V2, decrypt_val
from core.models import Equipamiento, PCGenerico, PerfilGenerico, Usuario


TARGETS = (
    (Usuario, ('password_gmail', 'password_vpn')),
    (Equipamiento, ('icloud_password', 'pin')),
    (PerfilGenerico, ('password',)),
    (PCGenerico, ('password',)),
)


class Command(BaseCommand):
    help = 'Verifica el formato y descifrado de todos los secretos persistidos.'

    def handle(self, *args, **kwargs):
        key = settings.FIELD_ENCRYPTION_KEY
        if not key:
            raise CommandError('FIELD_ENCRYPTION_KEY no está configurada.')
        try:
            Fernet(key.encode('ascii'))
        except (TypeError, ValueError, UnicodeError) as exc:
            raise CommandError('FIELD_ENCRYPTION_KEY no es una clave Fernet válida.') from exc

        invalid = []
        checked = 0
        for model, fields in TARGETS:
            for row in model.objects.values_list('pk', *fields).iterator(chunk_size=500):
                pk, *values = row
                for field, value in zip(fields, values):
                    if not value:
                        continue
                    reference = f'{model.__name__}:{pk}:{field}'
                    if not value.startswith(ENC_V2):
                        invalid.append(reference)
                        continue
                    try:
                        decrypt_val(value)
                    except (RuntimeError, ValueError, UnicodeError, TypeError):
                        invalid.append(reference)
                    else:
                        checked += 1

        if invalid:
            for reference in invalid[:50]:
                self.stdout.write(reference)
            raise CommandError(
                f'Hay {len(invalid)} secretos sin formato ENC2:: válido o que no se pueden descifrar.'
            )
        self.stdout.write(self.style.SUCCESS(f'OK: {checked} secretos ENC2:: descifrados correctamente.'))
