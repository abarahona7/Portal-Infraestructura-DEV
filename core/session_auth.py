from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import PortalSession


class PortalSessionError(Exception):
    pass


def get_active_portal_session(session_id, user_id=None):
    if not session_id:
        raise PortalSessionError('La sesión no tiene un identificador válido.')

    try:
        portal_session = PortalSession.objects.select_related('user').get(
            pk=session_id
        )
    except (PortalSession.DoesNotExist, ValueError, TypeError) as exc:
        raise PortalSessionError('La sesión no existe.') from exc

    if user_id is not None and str(portal_session.user_id) != str(user_id):
        raise PortalSessionError('La sesión no pertenece al usuario autenticado.')

    if portal_session.revoked_at is not None:
        raise PortalSessionError('La sesión fue cerrada.')

    idle_limit = timedelta(seconds=settings.PORTAL_IDLE_TIMEOUT_SECONDS)
    if timezone.now() - portal_session.last_activity >= idle_limit:
        portal_session.revoked_at = timezone.now()
        portal_session.save(update_fields=['revoked_at'])
        raise PortalSessionError('Sesión expirada por inactividad.')

    return portal_session


def touch_portal_session(portal_session):
    now = timezone.now()
    PortalSession.objects.filter(
        pk=portal_session.pk,
        revoked_at__isnull=True,
    ).update(last_activity=now)
    portal_session.last_activity = now
    return portal_session


def revoke_portal_session(session_id):
    if not session_id:
        return

    try:
        PortalSession.objects.filter(
            pk=session_id,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
    except (ValueError, TypeError):
        return
