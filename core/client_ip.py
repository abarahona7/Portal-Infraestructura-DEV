"""Obtención segura de IP cuando Django está detrás de proxies conocidos."""

from ipaddress import ip_address, ip_network

from django.conf import settings


def _valid_ip(value):
    try:
        return str(ip_address(value))
    except (TypeError, ValueError):
        return None


def _is_trusted_proxy(value):
    remote = _valid_ip(value)
    if remote is None:
        return False
    address = ip_address(remote)
    for configured in settings.PORTAL_TRUSTED_PROXY_IPS:
        try:
            if address in ip_network(configured, strict=False):
                return True
        except ValueError:
            continue
    return False


def get_client_ip_from_meta(meta):
    remote = _valid_ip(meta.get('REMOTE_ADDR'))
    if not _is_trusted_proxy(remote):
        return remote

    forwarded = meta.get('HTTP_X_FORWARDED_FOR', '')
    candidate = forwarded.split(',', 1)[0].strip()
    return _valid_ip(candidate) or remote


def get_client_ip(request):
    return get_client_ip_from_meta(request.META)


def get_websocket_client_ip(scope):
    client = scope.get('client') or (None, None)
    remote = client[0]
    headers = {
        name.lower(): value
        for name, value in scope.get('headers', [])
    }
    forwarded = headers.get(b'x-forwarded-for', b'').decode('latin1')
    return get_client_ip_from_meta({
        'REMOTE_ADDR': remote,
        'HTTP_X_FORWARDED_FOR': forwarded,
    })
