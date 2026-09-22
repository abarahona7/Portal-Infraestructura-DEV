from django.core.management.base import BaseCommand, CommandError
from core.models import Usuario, Equipamiento, PerfilGenerico, PCGenerico
TARGETS=[(Usuario,['password_gmail','password_vpn']),(Equipamiento,['icloud_password','pin']),(PerfilGenerico,['password']),(PCGenerico,['password'])]
class Command(BaseCommand):
    help='Verifica que todos los secretos persistidos usen ENC2::.'
    def handle(self,*args,**kwargs):
        legacy=[]
        for model,fields in TARGETS:
            for obj in model.objects.all().iterator():
                for field in fields:
                    value=getattr(obj,field,None)
                    if value and not value.startswith('ENC2::'):
                        legacy.append(f'{model.__name__}:{obj.pk}:{field}')
        if legacy:
            for item in legacy[:50]: self.stdout.write(item)
            raise CommandError(f'Quedan {len(legacy)} secretos fuera de ENC2::.')
        self.stdout.write(self.style.SUCCESS('OK: no quedan secretos legacy/plaintext.'))
