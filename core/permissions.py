from rest_framework.permissions import BasePermission, SAFE_METHODS

ROLE_VIEWER = 'Visualizador'
ROLE_OPERATOR = 'Operador Infraestructura'
ROLE_ADMIN = 'Administrador'
_ROLE_NOT_CACHED = object()


def get_role(user):
    if not user or not user.is_authenticated:
        return None
    cached_role = getattr(user, '_portal_role_cache', _ROLE_NOT_CACHED)
    if cached_role is not _ROLE_NOT_CACHED:
        return cached_role
    if user.is_superuser:
        role = ROLE_ADMIN
    else:
        names = set(user.groups.values_list('name', flat=True))
        role = next((name for name in (ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER) if name in names), None)
    user._portal_role_cache = role
    return role


def is_admin(user):
    return get_role(user) == ROLE_ADMIN


class HasPortalRole(BasePermission):
    """Require an authenticated account with a current portal role."""

    message = 'Tu cuenta no tiene un rol activo en el portal.'

    def has_permission(self, request, view):
        return get_role(request.user) is not None


class PortalRolePermission(BasePermission):
    """
    Permisos del portal aplicados en backend.

    - Visualizador: solo lectura en los viewsets que lo habiliten
      explícitamente con ``viewer_read_only = True``.
    - Operador Infraestructura y Administrador: lectura, creación y edición.
    - Ningún rol del portal puede retirar registros por DELETE.

    De esta forma no dependemos de ocultar botones en el frontend.
    """

    message = 'Tu rol no tiene permisos para realizar esta acción.'

    def has_permission(self, request, view):
        role = get_role(request.user)
        if not role:
            return False

        if role == ROLE_VIEWER:
            return (
                request.method in SAFE_METHODS
                and bool(getattr(view, 'viewer_read_only', False))
            )

        if request.method in SAFE_METHODS:
            return True

        if request.method == 'DELETE':
            return False

        return role in {ROLE_OPERATOR, ROLE_ADMIN}
