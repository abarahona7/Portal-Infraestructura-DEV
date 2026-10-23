"""Límites de uso del portal con claves seguras y ámbitos explícitos."""

import hashlib
import logging
import re

from rest_framework.exceptions import APIException
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle
from rest_framework.settings import api_settings

from .client_ip import get_client_ip


logger = logging.getLogger('portal.security')


class SecurityDependencyUnavailable(APIException):
    status_code = 503
    default_detail = 'El servicio de seguridad no está disponible. Intenta nuevamente más tarde.'
    default_code = 'security_dependency_unavailable'


class CacheFailClosedMixin:
    """Niega la operación con respuesta controlada si el límite no puede comprobarse."""

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except SecurityDependencyUnavailable:
            raise
        except Exception as exc:
            logger.exception(
                'security_cache_unavailable',
                extra={
                    'event': 'SECURITY_CACHE_UNAVAILABLE',
                    'reason': type(exc).__name__,
                    'result': 'denied',
                },
            )
            raise SecurityDependencyUnavailable() from exc


def _digest(value):
    return hashlib.sha256(str(value).casefold().encode('utf-8')).hexdigest()


class FlexibleWindowMixin:
    def parse_rate(self, rate):
        if rate is None:
            return None, None
        match = re.fullmatch(r'(\d+)/(\d+)(s|sec|m|min|h|hour|d|day)', rate)
        if not match:
            return super().parse_rate(rate)
        count, amount, unit = match.groups()
        seconds = {
            's': 1, 'sec': 1,
            'm': 60, 'min': 60,
            'h': 3600, 'hour': 3600,
            'd': 86400, 'day': 86400,
        }[unit]
        return int(count), int(amount) * seconds


class DynamicRateMixin:
    def get_rate(self):
        if not getattr(self, 'scope', None):
            return None
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope)


class ClientIPRateThrottle(CacheFailClosedMixin, DynamicRateMixin, SimpleRateThrottle):
    scope = None

    def get_cache_key(self, request, view):
        client_ip = get_client_ip(request)
        if not client_ip:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': _digest(client_ip),
        }


class LoginIPThrottle(ClientIPRateThrottle):
    scope = 'login_ip'


class LoginUsernameThrottle(CacheFailClosedMixin, FlexibleWindowMixin, DynamicRateMixin, SimpleRateThrottle):
    scope = 'login_username'

    def get_cache_key(self, request, view):
        data = getattr(request, 'data', None)
        if data is None:
            data = getattr(request, 'POST', {})
        username = str(data.get('username', '')).strip()
        if not username:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': _digest(username),
        }


class AdminLoginIPThrottle(LoginIPThrottle):
    scope = 'admin_login_ip'


class AdminLoginUsernameThrottle(LoginUsernameThrottle):
    scope = 'admin_login_username'


class RefreshIPThrottle(ClientIPRateThrottle):
    scope = 'refresh'


class PortalAnonRateThrottle(ClientIPRateThrottle):
    scope = 'api_anon'

    def allow_request(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        return super().allow_request(request, view)


class PortalUserRateThrottle(CacheFailClosedMixin, DynamicRateMixin, UserRateThrottle):
    scope = 'api_user'


class SecretRevealThrottle(CacheFailClosedMixin, DynamicRateMixin, UserRateThrottle):
    scope = 'secret_reveal'


class HeavyOperationThrottle(CacheFailClosedMixin, DynamicRateMixin, UserRateThrottle):
    scope = 'heavy'
