"""Reglas transaccionales para asignar IP a usuarios y servidores."""

from ipaddress import ip_address, ip_network

from django.db import transaction

from core.models import IP, Servidor, Usuario


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


class IpAssignmentError(Exception):
    """Conflicto de negocio que puede mostrarse en la API."""


def validate_user_ip(ip, user_id=None):
    parsed_ip = ip_address(ip.direccion_ip)
    if not any(parsed_ip in network for network in IP_ALLOWED_NETWORKS):
        raise IpAssignmentError(
            'La IP no pertenece a un segmento administrado en Gestión IPs.'
        )
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


def _reserve_user_ip(ip_id, user_id):
    IP.objects.filter(pk=ip_id).update(
        usuario_id=user_id,
        estado='RESERVADA',
        asignado_otro=None,
    )


def _reserve_server_ip(ip_id, hostname):
    IP.objects.filter(pk=ip_id).update(
        usuario=None,
        asignado_otro=f'Servidor: {hostname}',
        estado='RESERVADA',
    )


def _release_ip(ip_id):
    IP.objects.filter(pk=ip_id, usuario__isnull=True).update(
        asignado_otro=None,
        estado='LIBRE',
    )


@transaction.atomic
def assign_ip_to_user(user_id, address):
    user = Usuario.objects.select_for_update().get(pk=user_id)
    current_ids = list(
        IP.objects.filter(usuario_id=user.pk).values_list('pk', flat=True)
    )

    if address is None:
        if current_ids:
            list(
                IP.objects.select_for_update()
                .filter(pk__in=current_ids)
                .order_by('pk')
            )
            IP.objects.filter(pk__in=current_ids).update(
                usuario=None,
                estado='LIBRE',
                asignado_otro=None,
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
        .filter(pk__in=set(current_ids) | {target_id})
        .order_by('pk')
    }
    target = locked_ips[target_id]
    validate_user_ip(target, user_id=user.pk)

    previous_ids = [ip_id for ip_id in current_ids if ip_id != target_id]
    if previous_ids:
        IP.objects.filter(pk__in=previous_ids).update(
            usuario=None,
            estado='LIBRE',
            asignado_otro=None,
        )
    _reserve_user_ip(target_id, user.pk)
    return target


@transaction.atomic
def create_server_with_ip(ip_id, attributes):
    try:
        locked_ip = IP.objects.select_for_update().get(pk=ip_id)
    except IP.DoesNotExist as exc:
        raise IpAssignmentError('La IP seleccionada ya no existe.') from exc

    validate_server_ip(locked_ip)
    server = Servidor.objects.create(ip=locked_ip, **attributes)
    _reserve_server_ip(locked_ip.pk, server.hostname)
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
        _release_ip(previous_ip_id)
    _reserve_server_ip(selected_ip.pk, server.hostname)
    return server
