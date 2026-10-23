"""Minimiza los datos bearer persistidos por la blacklist de SimpleJWT."""

from rest_framework_simplejwt.token_blacklist.models import OutstandingToken


REDACTED_TOKEN_PREFIX = 'redacted:jti:'


def redact_outstanding_token(token):
    """Conserva JTI/expiración para blacklist sin almacenar el JWT reutilizable."""
    jti = str(token['jti'])
    OutstandingToken.objects.filter(jti=jti).exclude(
        token=f'{REDACTED_TOKEN_PREFIX}{jti}',
    ).update(token=f'{REDACTED_TOKEN_PREFIX}{jti}')

