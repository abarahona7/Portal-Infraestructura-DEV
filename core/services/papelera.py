"""Archivado reversible de los registros administrados por el portal."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.audit import get_current_audit_username
from core.models import (
    Anexo, Departamento, Equipamiento, HistorialAnexo, HistorialAsignacionIP,
    HistorialEquipo, HistorialPCGenerico, HistorialPerfilGenerico,
    HistorialServidor, HistorialUsuario, IP, PapeleraEvento, PCGenerico,
    PerfilGenerico, Servidor, SubArea, TipoAsignacionIP, Usuario,
    liberar_equipos_usuario,
)
from core.realtime import schedule_change
from core.services.asignacion_ips import assign_ip_to_user, release_ip_for_owner


ARCHIVABLE_MODELS = {
    'usuarios': Usuario,
    'equipos': Equipamiento,
    'perfiles-genericos': PerfilGenerico,
    'anexos': Anexo,
    'ips': IP,
    'pcs-genericos': PCGenerico,
    'servidores': Servidor,
    'departamentos': Departamento,
    'subareas': SubArea,
}


def _write_history(instance, action, detail):
    actor = get_current_audit_username() or 'Sistema'
    fields = {'accion': action, 'modificado_por': actor, 'observacion': detail}
    if isinstance(instance, Usuario):
        HistorialUsuario.objects.create(usuario=instance, **fields)
    elif isinstance(instance, Equipamiento):
        HistorialEquipo.objects.create(equipo=instance, **fields)
    elif isinstance(instance, PerfilGenerico):
        HistorialPerfilGenerico.objects.create(
            perfil=instance, perfil_nombre=instance.nombre or '',
            perfil_usuario=instance.usuario, **fields,
        )
    elif isinstance(instance, Anexo):
        HistorialAnexo.objects.create(anexo=instance, **fields)
    elif isinstance(instance, PCGenerico):
        HistorialPCGenerico.objects.create(pc=instance, **fields)
    elif isinstance(instance, Servidor):
        HistorialServidor.objects.create(
            servidor=instance, servidor_hostname=instance.hostname, **fields,
        )
    elif isinstance(instance, IP):
        HistorialAsignacionIP.objects.create(
            ip=instance, direccion_ip=instance.direccion_ip,
            accion='ARCHIVO' if action == 'ARCHIVO' else 'RESTAURACION',
            realizado_por=actor,
        )


def _module_for(instance):
    return next(key for key, model in ARCHIVABLE_MODELS.items() if isinstance(instance, model))


@transaction.atomic
def archive_record(instance):
    """Retira el registro de la operación activa sin borrar sus datos ni su PK."""
    instance = type(instance).objects.select_for_update().get(pk=instance.pk)
    context = {}
    history_parts = ['Registro:::Activo:::En Papelera']
    if isinstance(instance, Usuario):
        context = {'estado': instance.estado, 'departamento_id': instance.departamento_id}
        assign_ip_to_user(instance.pk, None)
        liberar_equipos_usuario(instance)
        for anexo in Anexo.objects.select_for_update().filter(usuario=instance):
            anexo.usuario = None
            anexo.save(update_fields=['usuario', 'estado'])
    elif isinstance(instance, Equipamiento):
        context = {'usuario_id': instance.usuario_id, 'estado': instance.estado}
        if instance.usuario_id:
            history_parts.append(f'Usuario asignado:::{instance.usuario.nombre_completo}:::Sin asignar')
            instance.usuario = None
            if instance.estado == 'ASIGNADO':
                instance.estado = 'STOCK'
            instance.fecha_asignacion = None
            instance.save(update_fields=['usuario', 'estado', 'fecha_asignacion'])
    elif isinstance(instance, Anexo):
        context = {'usuario_id': instance.usuario_id}
        if instance.usuario_id:
            history_parts.append(f'Usuario asignado:::{instance.usuario.nombre_completo}:::Sin asignar')
            instance.usuario = None
            instance.save(update_fields=['usuario', 'estado'])
    elif isinstance(instance, (Servidor, PCGenerico)):
        context = {'ip_id': instance.ip_id}
        if instance.ip_id:
            history_parts.append(f'Dirección IP:::{instance.ip.direccion_ip}:::Liberada')
            kind = TipoAsignacionIP.SERVIDOR if isinstance(instance, Servidor) else TipoAsignacionIP.PC_GENERICO
            release_ip_for_owner(instance.ip_id, kind, instance.pk)
            instance.ip = None
            instance.save(update_fields=['ip'])
    elif isinstance(instance, IP):
        if (instance.estado != 'LIBRE' or instance.usuario_id or instance.asignado_otro
                or hasattr(instance, 'servidor') or hasattr(instance, 'pc_generico')
                or hasattr(instance, 'asignacion_activa')):
            raise ValidationError({'detail': 'Solo se puede enviar a Papelera una IP libre y sin asignaciones.'})

    type(instance).all_objects.filter(pk=instance.pk).update(
        deleted_at=timezone.now(), deleted_by=get_current_audit_username() or 'Sistema',
        archive_context=context,
    )
    instance.refresh_from_db()
    _write_history(instance, 'ARCHIVO', '||'.join(history_parts))
    PapeleraEvento.objects.create(
        modulo=_module_for(instance), registro_id=instance.pk,
        accion='ARCHIVO', realizado_por=get_current_audit_username() or 'Sistema',
        detalle='Registro enviado a Papelera; las asignaciones liberadas no se recuperan automáticamente.',
    )
    schedule_change(instance, 'deleted')
    return instance


@transaction.atomic
def restore_record(module, record_id):
    model = ARCHIVABLE_MODELS.get(module)
    if model is None:
        raise ValidationError({'detail': 'Módulo desconocido.'})
    instance = model.all_objects.select_for_update().filter(
        pk=record_id, deleted_at__isnull=False,
    ).first()
    if instance is None:
        raise ValidationError({'detail': 'El registro no está en Papelera.'})

    for parent_field in ('departamento', 'subarea'):
        parent_id = getattr(instance, f'{parent_field}_id', None)
        if parent_id:
            parent = getattr(instance, parent_field)
            if parent.deleted_at is not None:
                raise ValidationError({'detail': f'Restaura primero el {parent_field} relacionado.'})

    model.all_objects.filter(pk=instance.pk).update(
        deleted_at=None, deleted_by=None, archive_context={},
    )
    instance.refresh_from_db()
    _write_history(instance, 'RESTAURACION', 'Registro:::En Papelera:::Activo')
    PapeleraEvento.objects.create(
        modulo=module, registro_id=instance.pk,
        accion='RESTAURACION', realizado_por=get_current_audit_username() or 'Sistema',
        detalle='Registro restaurado; las asignaciones deben revisarse antes de reasignarlas.',
    )
    schedule_change(instance, 'created')
    return instance
