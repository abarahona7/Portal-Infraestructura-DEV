"""Registro seguro y tolerante a fallos de eventos de seguridad."""

import logging
import hashlib
import re

from django.core.cache import cache

from .client_ip import get_client_ip
from .models import SecurityAuditLog


logger = logging.getLogger('portal.security')
_CONTROL_CHARACTERS = re.compile(r'[\x00-\x1f\x7f]+')
_ALERT_RULES = {
    'LOGIN_FAILED': (5, 15 * 60),
    'ACCESS_DENIED': (10, 5 * 60),
    'RATE_LIMITED': (3, 10 * 60),
    'API_UNHANDLED_EXCEPTION': (5, 5 * 60),
    'DATABASE_UNAVAILABLE': (3, 5 * 60),
    'SECRET_REVEAL': (10, 60 * 60),
}


def _clean(value, limit):
    if value in (None, ''):
        return ''
    return _CONTROL_CHARACTERS.sub(' ', str(value)).strip()[:limit]


def _evaluate_alert(event, actor, client_ip, request_id):
    rule = _ALERT_RULES.get(event)
    if not rule:
        return
    threshold, window = rule
    identity = hashlib.sha256(
        f'{event}|{actor}|{client_ip}'.encode('utf-8')
    ).hexdigest()
    key = f'security-alert:{identity}'
    try:
        if cache.add(key, 1, timeout=window):
            count = 1
        else:
            count = cache.incr(key)
    except Exception:
        logger.exception(
            'security_alert_counter_unavailable',
            extra={'event': event, 'result': 'alert_counter_failed'},
        )
        return
    if count == threshold:
        logger.critical(
            'security_alert_threshold_reached',
            extra={
                'event': event,
                'actor': actor,
                'client_ip': client_ip,
                'result': 'alert',
                'request_id': request_id,
                'reason': f'{threshold}_events_in_{window}_seconds',
            },
        )


def emit_security_event(
    *, event, success, actor='', role='', module='', object_id='', detail='',
    client_ip=None, request_id=None,
):
    """Emite JSON y evalúa alertas sin escribir otra fila de auditoría."""
    cleaned = {
        'event': _clean(event, 80),
        'actor': _clean(actor, 150),
        'role': _clean(role, 80),
        'module': _clean(module, 80),
        'object_id': _clean(object_id, 80),
        'detail': _clean(detail, 255),
    }
    level = logging.INFO if success else logging.WARNING
    logger.log(
        level,
        'security_event',
        extra={
            'event': cleaned['event'],
            'actor': cleaned['actor'],
            'role': cleaned['role'],
            'security_module': cleaned['module'],
            'security_object_id': cleaned['object_id'],
            'client_ip': client_ip,
            'result': 'success' if success else 'denied',
            'request_id': request_id,
        },
    )
    _evaluate_alert(cleaned['event'], cleaned['actor'], client_ip, request_id)
    return cleaned


def record_security_event(
    *,
    event,
    success,
    request=None,
    actor='',
    role='',
    module='',
    object_id='',
    detail='',
):
    """Registra el evento sin permitir que la auditoría cambie el resultado seguro."""
    user = getattr(request, 'user', None) if request is not None else None
    if not actor and user is not None and getattr(user, 'is_authenticated', False):
        actor = user.get_username()
    client_ip = get_client_ip(request) if request is not None else None
    request_id = getattr(request, 'request_id', None) if request is not None else None
    cleaned = emit_security_event(
        event=event,
        success=success,
        actor=actor,
        role=role,
        module=module,
        object_id=object_id,
        detail=detail,
        client_ip=client_ip,
        request_id=request_id,
    )
    try:
        SecurityAuditLog.objects.create(
            event=cleaned['event'],
            actor=cleaned['actor'] or None,
            module=cleaned['module'] or None,
            object_id_text=cleaned['object_id'] or None,
            success=success,
            detail=cleaned['detail'] or None,
            ip_address=client_ip,
            request_id=request_id,
        )
        return True
    except Exception:
        logger.exception(
            'security_audit_persistence_failed',
            extra={
                'event': cleaned['event'],
                'actor': cleaned['actor'],
                'role': cleaned['role'],
                'security_module': cleaned['module'],
                'security_object_id': cleaned['object_id'],
                'result': 'audit_failed',
            },
        )
        return False
