"""Validadores reutilizables para entradas persistidas por el portal."""

import unicodedata

from rest_framework.exceptions import ValidationError


MAX_ENCRYPTED_PLAINTEXT_BYTES = 127
_ALLOWED_TEXT_CONTROLS = {'\t', '\n'}


def validate_no_unsafe_control_characters(value):
    """Rechaza NUL y controles invisibles; conserva saltos de línea normales."""
    if not isinstance(value, str):
        return
    if any(
        character not in _ALLOWED_TEXT_CONTROLS
        and unicodedata.category(character) == 'Cc'
        for character in value
    ):
        raise ValidationError('El texto contiene caracteres de control no permitidos.')


def validate_encrypted_plaintext(value):
    """Garantiza que el valor cifrado con Fernet quepa en CharField(255)."""
    if value in (None, ''):
        return
    validate_no_unsafe_control_characters(value)
    if len(value.encode('utf-8')) > MAX_ENCRYPTED_PLAINTEXT_BYTES:
        raise ValidationError(
            'El secreto es demasiado largo; permite un máximo de 127 bytes.'
        )
