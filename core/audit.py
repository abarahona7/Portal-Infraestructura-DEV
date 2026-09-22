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