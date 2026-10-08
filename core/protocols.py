"""Confirmaciones exigidas antes de cambiar custodias o estados operativos."""

USER_STATUS_CHECKS = {
    'BAJA': (
        ('equipos', 'Revisé la devolución física de los equipos e insumos asignados.'),
        ('ip', 'Confirmé que se liberará la dirección IP del usuario.'),
        ('anexo', 'Confirmé que se liberará el anexo del usuario.'),
    ),
    'LICENCIA': (
        ('ip', 'Confirmé que se liberará la dirección IP del usuario.'),
        ('custodia', 'Verifiqué que sus equipos, insumos y anexo seguirán asignados.'),
    ),
    'ACTIVO': (
        ('reactivacion', 'Verifiqué los datos y accesos antes de reactivar al usuario.'),
    ),
}

EQUIPMENT_CHECKS = (
    ('custodia', 'Verifiqué físicamente la entrega o devolución del equipo.'),
    ('identidad', 'Comprobé la identidad del usuario asignado, cuando corresponde.'),
    ('estado', 'Revisé que el estado y la asignación registrados sean correctos.'),
)


def required_user_checks(instance, attrs):
    if instance is None or attrs.get('estado', instance.estado) == instance.estado:
        return ()
    return USER_STATUS_CHECKS[attrs['estado']]


def required_equipment_checks(instance, attrs):
    if instance is None:
        return ()
    user = attrs.get('usuario', instance.usuario)
    user_id = getattr(user, 'pk', None)
    state = attrs.get('estado', instance.estado)
    if user_id is None and state == 'ASIGNADO':
        state = 'STOCK'
    elif user_id is not None and state == 'STOCK':
        state = 'ASIGNADO'
    if user_id == instance.usuario_id and state == instance.estado:
        return ()
    return EQUIPMENT_CHECKS


def validate_confirmations(required, received):
    """Client IDs are checked against the server's complete, fixed protocol."""
    expected = {item_id for item_id, _ in required}
    return set(received or ()) == expected and len(received or ()) == len(expected)


def confirmation_observation(required):
    return '||'.join(f'Confirmación:::{label}:::Confirmado' for _, label in required)
