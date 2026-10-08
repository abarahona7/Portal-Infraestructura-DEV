"""Confirmaciones exigidas antes de cambiar custodias o estados operativos."""

USER_STATUS_CHECKS = {
    'BAJA': (
        ('equipos', 'Revisé la devolución física de los equipos asignados.'),
        ('ip', 'Confirmé que se liberará la dirección IP del usuario.'),
        ('anexo', 'Confirmé que se liberará el anexo del usuario.'),
    ),
    'LICENCIA': (
        ('ip', 'Confirmé que se liberará la dirección IP del usuario.'),
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

    next_status = attrs['estado']
    if next_status == 'ACTIVO':
        return USER_STATUS_CHECKS['ACTIVO']

    # Solo confirmar recursos que realmente cambiarán o seguirán en custodia.
    # El campo legado Usuario.anexo no representa una asignación de Anexo.
    from .models import Anexo, IP

    has_equipment = instance.equipos.exists()
    has_ip = IP.objects.filter(usuario_id=instance.pk).exists()
    has_extension = Anexo.objects.filter(usuario_id=instance.pk).exists()

    if next_status == 'BAJA':
        assigned = {'equipos': has_equipment, 'ip': has_ip, 'anexo': has_extension}
        checks = tuple(item for item in USER_STATUS_CHECKS['BAJA'] if assigned[item[0]])
    else:
        checks = list(USER_STATUS_CHECKS['LICENCIA'] if has_ip else ())
        if has_equipment or has_extension:
            if has_equipment and has_extension:
                custody_label = 'Verifiqué que los equipos y el anexo seguirán asignados durante la licencia.'
            elif has_equipment:
                custody_label = 'Verifiqué que los equipos seguirán asignados durante la licencia.'
            else:
                custody_label = 'Verifiqué que el anexo seguirá asignado durante la licencia.'
            checks.append((
                'custodia',
                custody_label,
            ))

    return tuple(checks) or ((
        'sin_recursos',
        'Verifiqué que el usuario no tiene equipos, IP ni anexo asignados.',
    ),)


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
