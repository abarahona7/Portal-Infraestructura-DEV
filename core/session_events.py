"""Eventos de cierre inmediato para conexiones WebSocket de una sesión."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


logger = logging.getLogger(__name__)


def session_group_name(session_id):
    return f'session.{session_id}'


def notify_session_revoked(session_id):
    if not session_id:
        return
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(
            session_group_name(session_id),
            {'type': 'session.revoked'},
        )
    except Exception:
        logger.exception('session_revocation_notification_failed')
