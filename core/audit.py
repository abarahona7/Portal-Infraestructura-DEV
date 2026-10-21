from contextvars import ContextVar


_current_audit_user = ContextVar(
    'current_audit_user',
    default=None
)


def set_current_audit_user(user):
    if isinstance(user, str):
        username = user.strip() or None
    elif user and getattr(user, 'is_authenticated', False):
        username = user.get_username()
    else:
        username = None

    # No guardar SimpleLazyObject/request.user en el contexto. Al restaurar
    # contexto bajo ASGI podría evaluarse dentro del loop async y consultar la
    # sesión fuera del hilo síncrono.
    return _current_audit_user.set(username)


def reset_current_audit_user(token):
    _current_audit_user.reset(token)


def get_current_audit_username():
    return _current_audit_user.get()
