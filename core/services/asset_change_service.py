"""Atomic equipment exchange: return the old asset and issue a replacement."""
import uuid

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Equipamiento
from core.services.asset_lifecycle_service import MovimientoConflict, registrar_movimiento


@transaction.atomic
def registrar_cambio_equipo(*, activo_origen_id, activo_destino_id, colaborador_id,
                           estado_fisico_origen,
                           estado_fisico_destino, accesorios_devueltos,
                           accesorios_entregados, observaciones, usuario_ti,
                           estado_operativo_origen='STOCK', request=None):
    """Both numbered actas and both asset updates commit together or not at all."""
    if activo_origen_id == activo_destino_id:
        raise ValidationError({'activo_destino_id': 'Seleccione un equipo de reemplazo diferente.'})
    assets = {asset.pk: asset for asset in Equipamiento.objects.select_for_update().filter(
        pk__in=[activo_origen_id, activo_destino_id]).order_by('pk')}
    old = assets.get(activo_origen_id)
    new = assets.get(activo_destino_id)
    if not old or not new:
        raise ValidationError({'activos': 'Seleccione dos equipos existentes.'})
    if old.usuario_id != colaborador_id or old.estado not in {'ASIGNADO', 'PRESTAMO'}:
        raise MovimientoConflict('ACTIVO_ORIGEN_NO_ASIGNADO', 'El equipo anterior no está asignado al colaborador indicado.')
    if new.usuario_id is not None or new.estado != 'STOCK':
        raise MovimientoConflict('ACTIVO_REEMPLAZO_NO_DISPONIBLE', 'El equipo de reemplazo debe estar disponible.')
    if estado_operativo_origen not in {'STOCK', 'MANTENCION'}:
        raise ValidationError({'estado_operativo_origen': 'El equipo anterior debe quedar disponible o en reparación.'})
    if not str(observaciones or '').strip():
        raise ValidationError({'observaciones': 'Indique el motivo del cambio de equipo.'})
    operation_id = uuid.uuid4()
    returned = registrar_movimiento(
        tipo_movimiento='DEVOLUCION', activo_id=old.pk,
        colaborador_origen_id=colaborador_id,
        estado_fisico=estado_fisico_origen, estado_operativo_resultante=estado_operativo_origen,
        accesorios_detalle=accesorios_devueltos, observaciones=observaciones,
        usuario_ti=usuario_ti, request=request, operacion_id=operation_id,
    )
    issued = registrar_movimiento(
        tipo_movimiento='CAMBIO', activo_id=new.pk,
        colaborador_destino_id=colaborador_id,
        estado_fisico=estado_fisico_destino, accesorios_detalle=accesorios_entregados,
        observaciones=observaciones, usuario_ti=usuario_ti, request=request,
        operacion_id=operation_id,
    )
    return operation_id, returned, issued
