from rest_framework.permissions import BasePermission, SAFE_METHODS

ROLE_VIEWER = 'Visualizador'
ROLE_OPERATOR = 'Operador Infraestructura'
ROLE_ADMIN = 'Administrador'


def get_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return ROLE_ADMIN
    names = set(user.groups.values_list('name', flat=True))
    if ROLE_ADMIN in names:
        return ROLE_ADMIN
    if ROLE_OPERATOR in names:
        return ROLE_OPERATOR
    if ROLE_VIEWER in names:
        return ROLE_VIEWER
    return None


def is_admin(user):
    return get_role(user) == ROLE_ADMIN


class PortalRolePermission(BasePermission):
    """
    Permisos del portal aplicados en backend.

    - Visualizador: solo lectura en los viewsets que lo habiliten
      explícitamente con ``viewer_read_only = True``.
    - Operador Infraestructura: lectura, creación y edición; sin DELETE.
    - Administrador/superuser: acceso completo.

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
            return role == ROLE_ADMIN

        return role in {ROLE_OPERATOR, ROLE_ADMIN}
