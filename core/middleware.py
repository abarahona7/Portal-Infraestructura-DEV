import logging
import math
import time
import uuid

from django.http import HttpResponse

from config.logging_utils import request_id_context
from .audit import reset_current_audit_user, set_current_audit_user
from .exceptions import record_rate_limit
from .throttles import (
    AdminLoginIPThrottle,
    AdminLoginUsernameThrottle,
    SecurityDependencyUnavailable,
)


logger = logging.getLogger('portal.request')


class AdminLoginRateLimitMiddleware:
    """Protege el acceso administrativo con límites por IP y usuario."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path != '/admin/login/' or request.method != 'POST':
            return self.get_response(request)

        throttles = [AdminLoginIPThrottle(), AdminLoginUsernameThrottle()]
        try:
            rejected = [throttle for throttle in throttles if not throttle.allow_request(request, None)]
        except SecurityDependencyUnavailable:
            logger.exception('admin_login_security_cache_unavailable')
            return HttpResponse(
                'El servicio de seguridad no está disponible. Intenta nuevamente más tarde.',
                status=503,
                content_type='text/plain; charset=utf-8',
            )
        if not rejected:
            return self.get_response(request)

        wait = max((throttle.wait() or 0 for throttle in rejected), default=1)
        record_rate_limit(
            request,
            'admin_login',
            str(request.POST.get('username', '')),
        )
        response = HttpResponse(
            'Demasiados intentos. Intenta nuevamente más tarde.',
            status=429,
            content_type='text/plain; charset=utf-8',
        )
        response['Retry-After'] = str(max(1, math.ceil(wait)))
        return response


class RequestContextMiddleware:
    """Asigna un ID único y registra duración y estado de cada solicitud."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = uuid.uuid4().hex
        request.request_id = request_id
        context_token = request_id_context.set(request_id)
        started_at = time.perf_counter()

        try:
            response = self.get_response(request)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            response['X-Request-ID'] = request_id
            logger.info(
                'request_completed',
                extra={
                    'http_method': request.method,
                    'http_path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                },
            )
            return response
        finally:
            request_id_context.reset(context_token)


class AuditActorMiddleware:
    """Expone el usuario autenticado a señales y servicios de auditoría."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current_audit_user(getattr(request, 'user', None))
        try:
            return self.get_response(request)
        finally:
            reset_current_audit_user(token)
