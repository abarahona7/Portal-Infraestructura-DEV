"""Límites de uso del portal con claves seguras y ámbitos explícitos."""

import hashlib
import re

from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle
from rest_framework.settings import api_settings

from .client_ip import get_client_ip


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


class ClientIPRateThrottle(DynamicRateMixin, SimpleRateThrottle):
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


class LoginUsernameThrottle(FlexibleWindowMixin, DynamicRateMixin, SimpleRateThrottle):
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


class PortalUserRateThrottle(DynamicRateMixin, UserRateThrottle):
    scope = 'api_user'


class SecretRevealThrottle(DynamicRateMixin, UserRateThrottle):
    scope = 'secret_reveal'


class HeavyOperationThrottle(DynamicRateMixin, UserRateThrottle):
    scope = 'heavy'
