"""Reglas transaccionales y registro central de asignaciones de IP."""

from ipaddress import ip_address, ip_network

from django.db import transaction

from core.audit import get_current_audit_username
from core.models import (
    AsignacionIP,
    HistorialAsignacionIP,
    IP,
    PCGenerico,
    Servidor,
    TipoAsignacionIP,
    Usuario,
)


IP_ALLOWED_NETWORKS = tuple(
    ip_network(network)
    for network in (
        '172.23.1.0/24',
        '172.24.1.0/24',
        '172.25.1.0/24',
        '192.168.10.0/24',
        '192.168.20.0/24',
        '192.168.30.0/24',
        '192.168.90.0/24',
    )
)
SERVER_IP_NETWORK = ip_network('172.23.1.0/24')
MANAGED_IP_SEGMENT_PREFIXES = {
    '172.23': '172.23.1.',
    '172.24': '172.24.1.',
    '172.25': '172.25.1.',
    '192.168.10': '192.168.10.',
    '192.168.20': '192.168.20.',
    '192.168.30': '192.168.30.',
    '192.168.90': '192.168.90.',
}


class IpAssignmentError(Exception):
    """Conflicto de negocio que puede mostrarse en la API."""


def _assignment_owner_id(assignment):
    if assignment.tipo == TipoAsignacionIP.USUARIO:
        return assignment.usuario_id
    if assignment.tipo == TipoAsignacionIP.SERVIDOR:
        return assignment.servidor_id
    if assignment.tipo == TipoAsignacionIP.PC_GENERICO:
        return assignment.pc_generico_id
    return None


def _assignment_owner_name(assignment):
    if assignment.tipo == TipoAsignacionIP.USUARIO and assignment.usuario_id:
        return assignment.usuario.nombre_completo
    if assignment.tipo == TipoAsignacionIP.SERVIDOR and assignment.servidor_id:
        return assignment.servidor.hostname
    if (
        assignment.tipo == TipoAsignacionIP.PC_GENERICO
        and assignment.pc_generico_id
    ):
        return assignment.pc_generico.hostname
    return assignment.detalle


def _write_assignment_history(
    ip,
    action,
    assignment_type=None,
    owner_id=None,
    owner_name=None,
):
    HistorialAsignacionIP.objects.create(
        ip=ip,
        direccion_ip=ip.direccion_ip,
        accion=action,
        tipo=assignment_type,
        propietario_id=owner_id,
        propietario_nombre=owner_name,
        realizado_por=get_current_audit_username(),
    )


def _get_locked_assignment(ip_id):
    return (
        AsignacionIP.objects.select_for_update()
        .select_related('usuario', 'servidor', 'pc_generico', 'ip')
        .filter(ip_id=ip_id)
        .first()
    )


def _clear_active_assignment(ip_id, expected_type=None, expected_owner_id=None):
    assignment = _get_locked_assignment(ip_id)
    if assignment is None:
        return

    current_owner_id = _assignment_owner_id(assignment)
    if expected_type and assignment.tipo != expected_type:
        raise IpAssignmentError(
            'La IP cambió de propietario durante la operación. Recarga e intenta nuevamente.'
        )
    if expected_owner_id and current_owner_id != expected_owner_id:
        raise IpAssignmentError(
            'La IP cambió de propietario durante la operación. Recarga e intenta nuevamente.'
        )

    _write_assignment_history(
        assignment.ip,
        'LIBERACION',
        assignment.tipo,
        current_owner_id,
        _assignment_owner_name(assignment),
    )
    assignment.delete()


def _set_active_assignment(
    ip,
    assignment_type,
    *,
    usuario=None,
    servidor=None,
    pc_generico=None,
    detalle=None,
    allow_legacy_replace=False,
):
    current = _get_locked_assignment(ip.pk)
    target_owner_id = (
        usuario.pk if usuario else
        servidor.pk if servidor else
        pc_generico.pk if pc_generico else
        None
    )
    target_detail = detalle.strip() if isinstance(detalle, str) else detalle

    if current:
        same_owner = (
            current.tipo == assignment_type
            and _assignment_owner_id(current) == target_owner_id
        )
        same_detail = (current.detalle or None) == (target_detail or None)
        if same_owner and same_detail:
            return current
        if not same_owner and not allow_legacy_replace:
            raise IpAssignmentError(
                'Esta IP ya pertenece a otro registro. Recarga e intenta nuevamente.'
            )
        _clear_active_assignment(ip.pk)

    owner_filter = None
    if usuario:
        owner_filter = {'usuario_id': usuario.pk}
    elif servidor:
        owner_filter = {'servidor_id': servidor.pk}
    elif pc_generico:
        owner_filter = {'pc_generico_id': pc_generico.pk}

    if owner_filter:
        previous = (
            AsignacionIP.objects.select_for_update()
            .select_related('usuario', 'servidor', 'pc_generico', 'ip')
            .filter(**owner_filter)
            .exclude(ip_id=ip.pk)
            .first()
        )
        if previous:
            previous_ip_id = previous.ip_id
            _clear_active_assignment(previous_ip_id)
            IP.objects.filter(pk=previous_ip_id).update(
                usuario=None,
                asignado_otro=None,
                estado='LIBRE',
            )

    assignment = AsignacionIP.objects.create(
        ip=ip,
        tipo=assignment_type,
        usuario=usuario,
        servidor=servidor,
        pc_generico=pc_generico,
        detalle=target_detail,
    )
    owner_name = (
        usuario.nombre_completo if usuario else
        servidor.hostname if servidor else
        pc_generico.hostname if pc_generico else
        target_detail
    )
    _write_assignment_history(
        ip,
        'ASIGNACION',
        assignment_type,
        target_owner_id,
        owner_name,
    )
    return assignment


def _validate_active_assignment(ip, expected_type, expected_owner_id=None):
    assignment = AsignacionIP.objects.filter(ip_id=ip.pk).first()
    if assignment is None:
        return

    if (
        assignment.tipo == expected_type
        and _assignment_owner_id(assignment) == expected_owner_id
    ):
        return

    owner_type = assignment.get_tipo_display().lower()
    raise IpAssignmentError(
        f'Esta IP ya tiene una asignación activa de tipo {owner_type}.'
    )


def validate_user_ip(ip, user_id=None):
    parsed_ip = ip_address(ip.direccion_ip)
    if not any(parsed_ip in network for network in IP_ALLOWED_NETWORKS):
        raise IpAssignmentError(
            'La IP no pertenece a un segmento administrado en Gestión IPs.'
        )
    _validate_active_assignment(ip, TipoAsignacionIP.USUARIO, user_id)
    if ip.usuario_id not in (None, user_id):
        raise IpAssignmentError('Esta IP ya está asignada a otro usuario.')
    if ip.asignado_otro:
        raise IpAssignmentError(
            'Esta IP está reservada para otro dispositivo o servicio.'
        )
    if ip.estado != 'LIBRE' and ip.usuario_id != user_id:
        raise IpAssignmentError(
            'Solo se pueden asignar IPs que estén en estado Libre.'
        )


def validate_server_ip(ip, server_id=None):
    parsed_ip = ip_address(ip.direccion_ip)
    if parsed_ip not in SERVER_IP_NETWORK or parsed_ip in (
        SERVER_IP_NETWORK.network_address,
        SERVER_IP_NETWORK.broadcast_address,
    ):
        raise IpAssignmentError(
            'Los servidores solo pueden usar IP del segmento 172.23.1.0/24.'
        )

    _validate_active_assignment(ip, TipoAsignacionIP.SERVIDOR, server_id)

    assigned_server_id = Servidor.objects.filter(ip_id=ip.pk).values_list(
        'pk', flat=True
    ).first()
    if assigned_server_id and assigned_server_id != server_id:
        raise IpAssignmentError('Esta IP ya está asignada a otro servidor.')

    is_current = bool(server_id and assigned_server_id == server_id)
    if is_current:
        if ip.usuario_id:
            raise IpAssignmentError('Esta IP ya está asignada a un usuario.')
        return

    if ip.usuario_id or ip.asignado_otro or ip.estado != 'LIBRE':
        raise IpAssignmentError(
            'Solo se pueden asignar IP que estén disponibles.'
        )


def validate_pc_generico_ip(ip, pc_id=None):
    parsed_ip = ip_address(ip.direccion_ip)
    network = next(
        (item for item in IP_ALLOWED_NETWORKS if parsed_ip in item),
        None,
    )
    if network is None or parsed_ip in (
        network.network_address,
        network.broadcast_address,
    ):
        raise IpAssignmentError(
            'La IP no pertenece a un segmento administrado en Gestión IPs.'
        )

    _validate_active_assignment(ip, TipoAsignacionIP.PC_GENERICO, pc_id)

    assigned_pc_id = PCGenerico.objects.filter(ip_id=ip.pk).values_list(
        'pk', flat=True
    ).first()
    if assigned_pc_id and assigned_pc_id != pc_id:
        raise IpAssignmentError('Esta IP ya está asignada a otro PC Genérico.')

    assigned_server_id = Servidor.objects.filter(ip_id=ip.pk).values_list(
        'pk', flat=True
    ).first()
    if assigned_server_id:
        raise IpAssignmentError('Esta IP ya está asignada a un servidor.')

    is_current = bool(pc_id and assigned_pc_id == pc_id)
    if is_current:
        if ip.usuario_id:
            raise IpAssignmentError('Esta IP ya está asignada a un usuario.')
        return

    if ip.usuario_id or ip.asignado_otro or ip.estado != 'LIBRE':
        raise IpAssignmentError(
            'Solo se pueden asignar IP que estén disponibles.'
        )


def _reserve_user_ip(ip, user):
    _set_active_assignment(
        ip,
        TipoAsignacionIP.USUARIO,
        usuario=user,
    )
    IP.objects.filter(pk=ip.pk).update(
        usuario_id=user.pk,
        estado='RESERVADA',
        asignado_otro=None,
    )


def _reserve_server_ip(ip, server):
    _set_active_assignment(
        ip,
        TipoAsignacionIP.SERVIDOR,
        servidor=server,
    )
    IP.objects.filter(pk=ip.pk).update(
        usuario=None,
        asignado_otro=f'Servidor: {server.hostname}',
        estado='RESERVADA',
    )


def _reserve_pc_generico_ip(ip, pc):
    _set_active_assignment(
        ip,
        TipoAsignacionIP.PC_GENERICO,
        pc_generico=pc,
    )
    IP.objects.filter(pk=ip.pk).update(
        usuario=None,
        asignado_otro=f'PC Genérico: {pc.hostname}',
        estado='RESERVADA',
    )


def _release_ip(ip_id, expected_type=None, expected_owner_id=None):
    _clear_active_assignment(ip_id, expected_type, expected_owner_id)
    IP.objects.filter(pk=ip_id).update(
        usuario=None,
        asignado_otro=None,
        estado='LIBRE',
    )


@transaction.atomic
def sync_ip_assignment_from_legacy(ip_id):
    """Sincroniza escrituras heredadas hacia el registro formal de asignación."""

    try:
        ip = (
            IP.objects.select_for_update()
            .select_related('usuario', 'servidor', 'pc_generico')
            .get(pk=ip_id)
        )
    except IP.DoesNotExist:
        return None

    server = getattr(ip, 'servidor', None)
    pc = getattr(ip, 'pc_generico', None)
    relation_count = sum(bool(item) for item in (ip.usuario_id, server, pc))
    if relation_count > 1:
        raise IpAssignmentError(
            'La IP tiene más de un propietario relacionado. Corrige la inconsistencia antes de continuar.'
        )

    if ip.usuario_id:
        return _set_active_assignment(
            ip,
            TipoAsignacionIP.USUARIO,
            usuario=ip.usuario,
            allow_legacy_replace=True,
        )
    if server:
        return _set_active_assignment(
            ip,
            TipoAsignacionIP.SERVIDOR,
            servidor=server,
            allow_legacy_replace=True,
        )
    if pc:
        return _set_active_assignment(
            ip,
            TipoAsignacionIP.PC_GENERICO,
            pc_generico=pc,
            allow_legacy_replace=True,
        )
    if ip.asignado_otro:
        return _set_active_assignment(
            ip,
            TipoAsignacionIP.OTRO,
            detalle=ip.asignado_otro,
            allow_legacy_replace=True,
        )

    _clear_active_assignment(ip.pk)
    return None


@transaction.atomic
def release_ip_for_owner(ip_id, assignment_type, owner_id):
    """Libera una IP antes de eliminar su propietario relacionado."""

    if not ip_id:
        return
    if not IP.objects.select_for_update().filter(pk=ip_id).exists():
        return
    _release_ip(ip_id, assignment_type, owner_id)


@transaction.atomic
def assign_ip_to_user(user_id, address):
    user = Usuario.objects.select_for_update().get(pk=user_id)
    current_ids = set(
        IP.objects.filter(usuario_id=user.pk).values_list('pk', flat=True)
    )
    active_ip_id = AsignacionIP.objects.filter(
        usuario_id=user.pk
    ).values_list('ip_id', flat=True).first()
    if active_ip_id:
        current_ids.add(active_ip_id)

    if address is None:
        if current_ids:
            list(
                IP.objects.select_for_update()
                .filter(pk__in=current_ids)
                .order_by('pk')
            )
            for ip_id in sorted(current_ids):
                _release_ip(
                    ip_id,
                    TipoAsignacionIP.USUARIO,
                    user.pk,
                )
        return None

    if user.estado in {'BAJA', 'LICENCIA'}:
        raise IpAssignmentError(
            'No se puede asignar una IP a un usuario en estado Baja o Licencia.'
        )

    try:
        target_id = IP.objects.only('pk').get(direccion_ip=address).pk
    except IP.DoesNotExist as exc:
        raise IpAssignmentError('La IP seleccionada ya no existe.') from exc

    locked_ips = {
        item.pk: item
        for item in IP.objects.select_for_update()
        .filter(pk__in=current_ids | {target_id})
        .order_by('pk')
    }
    target = locked_ips[target_id]
    validate_user_ip(target, user_id=user.pk)

    previous_ids = sorted(ip_id for ip_id in current_ids if ip_id != target_id)
    for ip_id in previous_ids:
        _release_ip(
            ip_id,
            TipoAsignacionIP.USUARIO,
            user.pk,
        )
    _reserve_user_ip(target, user)
    return target


@transaction.atomic
def create_server_with_ip(ip_id, attributes):
    try:
        locked_ip = IP.objects.select_for_update().get(pk=ip_id)
    except IP.DoesNotExist as exc:
        raise IpAssignmentError('La IP seleccionada ya no existe.') from exc

    validate_server_ip(locked_ip)
    server = Servidor.objects.create(ip=locked_ip, **attributes)
    _reserve_server_ip(locked_ip, server)
    return server


@transaction.atomic
def update_server_with_ip(server_id, ip_id, attributes):
    server = Servidor.objects.select_for_update().get(pk=server_id)
    previous_ip_id = server.ip_id
    ip_ids = {ip_id}
    if previous_ip_id:
        ip_ids.add(previous_ip_id)

    locked_ips = {
        item.pk: item
        for item in IP.objects.select_for_update()
        .filter(pk__in=ip_ids)
        .order_by('pk')
    }
    try:
        selected_ip = locked_ips[ip_id]
    except KeyError as exc:
        raise IpAssignmentError('La IP seleccionada ya no existe.') from exc

    validate_server_ip(selected_ip, server_id=server.pk)
    for field, value in attributes.items():
        setattr(server, field, value)
    server.ip = selected_ip
    server.save()

    if previous_ip_id and previous_ip_id != selected_ip.pk:
        _release_ip(
            previous_ip_id,
            TipoAsignacionIP.SERVIDOR,
            server.pk,
        )
    _reserve_server_ip(selected_ip, server)
    return server


@transaction.atomic
def create_pc_generico_with_ip(address, attributes):
    if address is None:
        return PCGenerico.objects.create(**attributes)

    try:
        target_id = IP.objects.only('pk').get(direccion_ip=address).pk
        locked_ip = IP.objects.select_for_update().get(pk=target_id)
    except IP.DoesNotExist as exc:
        raise IpAssignmentError('La IP seleccionada ya no existe.') from exc

    validate_pc_generico_ip(locked_ip)
    pc = PCGenerico.objects.create(ip=locked_ip, **attributes)
    _reserve_pc_generico_ip(locked_ip, pc)
    return pc


@transaction.atomic
def update_pc_generico_with_ip(pc_id, address, attributes):
    pc = PCGenerico.objects.select_for_update().get(pk=pc_id)
    previous_ip_id = pc.ip_id

    target_id = None
    if address is not None:
        try:
            target_id = IP.objects.only('pk').get(direccion_ip=address).pk
        except IP.DoesNotExist as exc:
            raise IpAssignmentError('La IP seleccionada ya no existe.') from exc

    ip_ids = {item for item in (previous_ip_id, target_id) if item is not None}
    locked_ips = {
        item.pk: item
        for item in IP.objects.select_for_update()
        .filter(pk__in=ip_ids)
        .order_by('pk')
    }

    selected_ip = None
    if target_id is not None:
        try:
            selected_ip = locked_ips[target_id]
        except KeyError as exc:
            raise IpAssignmentError('La IP seleccionada ya no existe.') from exc
        validate_pc_generico_ip(selected_ip, pc_id=pc.pk)

    for field, value in attributes.items():
        setattr(pc, field, value)
    pc.ip = selected_ip
    pc.save()

    if previous_ip_id and previous_ip_id != target_id:
        _release_ip(
            previous_ip_id,
            TipoAsignacionIP.PC_GENERICO,
            pc.pk,
        )
    if selected_ip:
        _reserve_pc_generico_ip(selected_ip, pc)
    return pc
