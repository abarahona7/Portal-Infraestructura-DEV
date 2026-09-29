"""Validation and canonical storage of Chilean RUT identifiers."""

import re

from django.core.exceptions import ValidationError


_RUT = re.compile(r'^(?:[0-9]{1,8}|[0-9]{1,2}\.[0-9]{3}\.[0-9]{3})-?[0-9Kk]$')


def validar_rut(value):
    """Return an undotted, upper-case RUT after checking its modulo-11 digit."""
    rut = str(value).strip()
    if not _RUT.fullmatch(rut):
        raise ValidationError({'rut': 'Ingrese un RUT válido con su dígito verificador.'})
    compact = rut.replace('.', '').replace('-', '').upper()
    body, check = compact[:-1], compact[-1]
    if not body or int(body) == 0:
        raise ValidationError({'rut': 'El RUT no puede ser cero.'})
    total = sum(int(digit) * (2 + index % 6) for index, digit in enumerate(reversed(body)))
    remainder = 11 - total % 11
    expected = '0' if remainder == 11 else 'K' if remainder == 10 else str(remainder)
    if check != expected:
        raise ValidationError({'rut': 'El dígito verificador del RUT es incorrecto.'})
    return f'{int(body)}-{expected}'
