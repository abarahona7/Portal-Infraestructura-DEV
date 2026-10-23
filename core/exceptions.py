"""Respuestas y auditoría comunes de errores de la API."""

import logging
import hashlib

from django.core.cache import cache
from django.db import OperationalError
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied, Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .client_ip import get_client_ip
from .security_events import record_security_event


logger = logging.getLogger(__name__)


def record_rate_limit(request, module, actor=''):
    client_ip = get_client_ip(request) if request is not None else None
    fingerprint = hashlib.sha256(
        f'{module}|{actor}|{client_ip}'.encode('utf-8')
    ).hexdigest()
    try:
        if not cache.add(f'rate-limit-audit:{fingerprint}', 1, timeout=60):
            return
    except Exception:
        logger.exception('rate_limit_audit_cache_failed')
    record_security_event(
            request=request,
            event='RATE_LIMITED',
            actor=actor,
            module=module,
            success=False,
            detail='Solicitud rechazada por límite de frecuencia.',
        )


def portal_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get('request')
    view = context.get('view')
    request_id = getattr(request, 'request_id', None)

    if response is None:
        is_database_unavailable = isinstance(exc, OperationalError)
        logger.error(
            'api_unhandled_exception',
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={
                'event': 'DATABASE_UNAVAILABLE' if is_database_unavailable else 'API_UNHANDLED_EXCEPTION',
                'status_code': 503 if is_database_unavailable else 500,
            },
        )
        record_security_event(
            request=request,
            event='DATABASE_UNAVAILABLE' if is_database_unavailable else 'API_UNHANDLED_EXCEPTION',
            success=False,
            module=getattr(view, 'basename', '') or getattr(request, 'path', 'api'),
            detail=type(exc).__name__,
        )
        return Response(
            {
                'detail': 'El servicio no pudo completar la operación.',
                'request_id': request_id,
            },
            status=(
                status.HTTP_503_SERVICE_UNAVAILABLE
                if is_database_unavailable
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
        )

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated, PermissionDenied)):
        record_security_event(
            request=request,
            event='ACCESS_DENIED',
            success=False,
            module=getattr(view, 'basename', '') or getattr(request, 'path', 'api'),
            detail=type(exc).__name__,
        )

    if response.status_code >= 500:
        record_security_event(
            request=request,
            event='SECURITY_DEPENDENCY_UNAVAILABLE',
            success=False,
            module=getattr(view, 'basename', '') or getattr(request, 'path', 'api'),
            detail=type(exc).__name__,
        )

    if not isinstance(exc, Throttled):
        return response

    actor = ''
    if request is not None and request.user and request.user.is_authenticated:
        actor = request.user.get_username()
    module = getattr(view, 'throttle_scope', None) or getattr(request, 'path', 'api')
    record_rate_limit(request, module, actor)

    response.data = {
        'detail': 'Demasiadas solicitudes. Intenta nuevamente más tarde.',
        'request_id': request_id,
    }
    return response
