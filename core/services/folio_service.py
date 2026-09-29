"""Transactional annual document numbering, serialized by MySQL row locks."""

import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import FolioContador


@transaction.atomic
def generar_siguiente_folio(tipo='ATI', *, anio=None):
    tipo = str(tipo).strip().upper()
    if not re.fullmatch(r'[A-Z]{1,10}', tipo):
        raise ValidationError('El tipo de documento debe contener entre 1 y 10 letras.')
    anio = timezone.localdate().year if anio is None else anio
    if not isinstance(anio, int) or isinstance(anio, bool) or not 2000 <= anio <= 9999:
        raise ValidationError('El año del folio no es válido.')

    # The unique key resolves concurrent creation of the first counter in a year.
    # Lock again after get_or_create: its IntegrityError recovery does not promise
    # a locked row when another transaction won the insertion race.
    FolioContador.objects.get_or_create(anio=anio, tipo_documento=tipo)
    contador = FolioContador.objects.select_for_update().get(anio=anio, tipo_documento=tipo)
    if contador.ultimo_folio >= 999999:
        raise ValidationError('Se agotó el correlativo anual de este documento.')
    contador.ultimo_folio += 1
    contador.save(update_fields=['ultimo_folio', 'fecha_actualizacion'])
    return f'{tipo}-{anio}-{contador.ultimo_folio:06d}'
