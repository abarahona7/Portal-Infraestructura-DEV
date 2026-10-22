"""Validadores adicionales de contraseña del portal."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class NoCurrentPasswordReuseValidator:
    def validate(self, password, user=None):
        if user is not None and user.pk and user.check_password(password):
            raise ValidationError(
                _('La nueva contraseña debe ser diferente de la actual.'),
                code='password_unchanged',
            )

    def get_help_text(self):
        return _('La nueva contraseña debe ser diferente de la actual.')
