import ipaddress
from contextvars import ContextVar


_current_audit_user = ContextVar(
    'current_audit_user',
    default=None
)


def set_current_audit_user(user):
    return _current_audit_user.set(user)


def reset_current_audit_user(token):
    _current_audit_user.reset(token)


def get_current_audit_username():
    user = _current_audit_user.get()

    if not user:
        return None

    if not getattr(user, 'is_authenticated', False):
        return None

    return user.get_username()


def get_request_ip(request):
    """Use the server-provided address, never an untrusted forwarded header."""
    if request is None:
        return None
    raw = request.META.get('REMOTE_ADDR')
    try:
        return str(ipaddress.ip_address(raw)) if raw else None
    except ValueError:
        return None
