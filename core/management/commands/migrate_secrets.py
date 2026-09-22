from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.crypto import migrate_value
from core.models import Usuario, Equipamiento, PerfilGenerico, PCGenerico

TARGETS = [
    (Usuario, ['password_gmail', 'password_vpn']),
    (Equipamiento, ['icloud_password', 'pin']),
    (PerfilGenerico, ['password']),
    (PCGenerico, ['password']),
]

class Command(BaseCommand):
    help = 'Migra secretos plaintext/ENC:: al formato ENC2:: usando FIELD_ENCRYPTION_KEY.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        changed = 0
        with transaction.atomic():
            for model, fields in TARGETS:
                for obj in model.objects.all().iterator():
                    updates=[]
                    for field in fields:
                        value=getattr(obj, field, None)
                        if value and not value.startswith('ENC2::'):
                            setattr(obj, field, migrate_value(value)); updates.append(field)
                    if updates:
                        model.objects.filter(pk=obj.pk).update(**{f:getattr(obj,f) for f in updates}); changed += len(updates)
            if opts['dry_run']:
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f'Secretos a migrar/migrados: {changed}'))
