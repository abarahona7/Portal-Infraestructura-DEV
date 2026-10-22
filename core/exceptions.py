"""Respuestas y auditoría comunes de errores de la API."""

import logging
import hashlib

from django.core.cache import cache
from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler

from .client_ip import get_client_ip
from .models import SecurityAuditLog


logger = logging.getLogger(__name__)


def record_rate_limit(request, module, actor=''):
    client_ip = get_client_ip(request) if request is not None else None
    fingerprint = hashlib.sha256(
        f'{module}|{actor}|{client_ip}'.encode('utf-8')
    ).hexdigest()
    if not cache.add(f'rate-limit-audit:{fingerprint}', 1, timeout=60):
        return
    try:
        SecurityAuditLog.objects.create(
            event='RATE_LIMITED',
            actor=actor[:150],
            module=module,
            success=False,
            detail='Solicitud rechazada por límite de frecuencia.',
            ip_address=client_ip,
            request_id=getattr(request, 'request_id', None),
        )
    except Exception:
        logger.exception('rate_limit_audit_failed')


def portal_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None or not isinstance(exc, Throttled):
        return response

    request = context.get('request')
    view = context.get('view')
    actor = ''
    if request is not None and request.user and request.user.is_authenticated:
        actor = request.user.get_username()
    module = getattr(view, 'throttle_scope', None) or getattr(request, 'path', 'api')
    record_rate_limit(request, module, actor)

    response.data = {
        'detail': 'Demasiadas solicitudes. Intenta nuevamente más tarde.',
    }
    return response
