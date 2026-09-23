from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .session_auth import PortalSessionError, get_active_portal_session


class PortalJWTAuthentication(JWTAuthentication):
    """Autenticación JWT vinculada a una sesión revocable del portal."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        try:
            get_active_portal_session(
                validated_token.get('sid'),
                user_id=user.pk,
            )
        except PortalSessionError as exc:
            raise AuthenticationFailed(str(exc), code='session_expired') from exc

        return user
