"""Atomic IT asset lifecycle movements and immutable documentary evidence."""

from copy import deepcopy
import hashlib
import json
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.audit import get_request_ip, reset_current_audit_user, set_current_audit_user
from core.models import (
    ActaEntrega, Equipamiento, ESTADOS_FISICOS, MovimientoActivo,
    SecurityAuditLog, Usuario,
)
from core.services.acta_entrega_pdf import generar_acta_custodia_pdf
from core.services.folio_service import generar_siguiente_folio


class MovimientoConflict(Exception):
    def __init__(self, codigo, detail):
        self.codigo = codigo
        self.detail = detail
        super().__init__(detail)


def _text(value):
    return ' '.join(str(value or '').strip().split())


def _colaborador_snapshot(colaborador):
    if colaborador is None:
        return None
    return {
        'id': colaborador.pk,
        'nombre_completo': colaborador.nombre_completo,
        'rut': colaborador.rut or '',
        'correo_corp': colaborador.correo_corp,
        'usuario_red': colaborador.usuario_red,
        'cargo': colaborador.cargo or '',
        'area': colaborador.departamento.nombre,
        'subarea': colaborador.subarea.nombre if colaborador.subarea_id else '',
        'centro_costo': colaborador.centro_costo or '',
        'ubicacion': colaborador.ubicacion,
    }


def _activo_snapshot(activo):
    return {
        'id': activo.pk,
        'tipo': activo.tipo,
        'marca': activo.marca,
        'modelo': activo.modelo,
        'numero_serie': activo.numero_serie or '',
        'af': activo.af or '',
        'imei': activo.imei or '',
        'mac_address': activo.mac_address or '',
        'hostname': activo.hostname or '',
        'token_qr': str(activo.token_qr),
        'estado': activo.estado,
        'estado_fisico': activo.estado_fisico,
        'ubicacion_actual': activo.ubicacion_actual,
        'usuario_id': activo.usuario_id,
        'fecha_asignacion': activo.fecha_asignacion.isoformat() if activo.fecha_asignacion else None,
    }


def accesorios_requeridos(activo):
    """Return the issued checklist, falling back to the legacy accessory text."""
    ultimo = activo.movimientos.filter(tipo_movimiento__in=['ASIGNACION', 'REASIGNACION', 'PRESTAMO', 'CAMBIO']).first()
    if ultimo is not None:
        return [item['nombre'] for item in ultimo.accesorios_detalle if item.get('entregado')]
    return list(dict.fromkeys(
        _text(nombre) for nombre in re.split(r'[,;\n]+', activo.accesorios or '') if _text(nombre)
    ))


def _validar_accesorios(items, *, activo, devolucion, exigir_maestro=False):
    if items is None:
        items = []
    if not isinstance(items, list) or len(items) > 20:
        raise ValidationError({'accesorios_detalle': 'Indique una lista de hasta 20 accesorios.'})
    normalized = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValidationError({'accesorios_detalle': 'Cada accesorio debe ser un objeto.'})
        nombre = _text(item.get('nombre'))
        nota = _text(item.get('nota'))
        entregado = item.get('entregado')
        if not nombre or len(nombre) > 100 or len(nota) > 200 or type(entregado) is not bool:
            raise ValidationError({'accesorios_detalle': 'Cada accesorio requiere nombre (máximo 100), entregado (booleano) y nota de hasta 200 caracteres.'})
        if nombre.casefold() in seen:
            raise ValidationError({'accesorios_detalle': 'No repita accesorios en la lista.'})
        if not entregado and not nota:
            raise ValidationError({'accesorios_detalle': f'Explique el accesorio faltante: {nombre}.'})
        seen.add(nombre.casefold())
        normalized.append({'nombre': nombre, 'entregado': entregado, 'nota': nota})
    if exigir_maestro and not activo.movimientos.filter(tipo_movimiento__in=['ASIGNACION', 'REASIGNACION', 'PRESTAMO', 'CAMBIO']).exists():
        missing = [name for name in re.split(r'[,;\n]+', activo.accesorios or '')
                   if _text(name) and _text(name).casefold() not in seen]
        if missing:
            raise ValidationError({'accesorios_detalle': 'Revise los accesorios registrados en el activo: ' + ', '.join(missing) + '.'})
    if devolucion:
        missing = [name for name in accesorios_requeridos(activo) if name.casefold() not in seen]
        if missing:
            raise ValidationError({'accesorios_detalle': 'Revise todos los accesorios entregados: ' + ', '.join(missing) + '.'})
    return normalized


@transaction.atomic
def registrar_movimiento(*, tipo_movimiento, activo_id, usuario_ti,
                         colaborador_destino_id=None, colaborador_origen_id=None,
                         ubicacion_destino, estado_fisico='USADO',
                         estado_operativo_resultante=None, accesorios_detalle=None,
                         observaciones='', request=None, qr_base_url=None, operacion_id=None):
    """Persist state, movement, numbered PDF and audit atomically after locking the asset."""
    supported = {'ASIGNACION', 'PRESTAMO', 'CAMBIO', 'DEVOLUCION', 'REASIGNACION',
                 'INGRESO_REPARACION', 'SALIDA_REPARACION', 'BAJA'}
    if tipo_movimiento not in supported:
        raise ValidationError({'tipo_movimiento': 'Tipo de movimiento no disponible.'})
    if tipo_movimiento == 'CAMBIO' and not operacion_id:
        raise ValidationError({'operacion_id': 'El cambio de equipo requiere una operación vinculada.'})
    if not getattr(usuario_ti, 'is_authenticated', False) or not usuario_ti.pk or not usuario_ti.is_active:
        raise ValidationError({'usuario_ti': 'Se requiere un operador autenticado y activo.'})
    ubicacion_destino = _text(ubicacion_destino)
    observaciones = str(observaciones or '').strip()
    if not ubicacion_destino or len(ubicacion_destino) > 100:
        raise ValidationError({'ubicacion_destino': 'Indique una ubicación de hasta 100 caracteres.'})
    if estado_fisico not in dict(ESTADOS_FISICOS):
        raise ValidationError({'estado_fisico': 'Seleccione un estado físico válido.'})
    if len(observaciones) > 2000:
        raise ValidationError({'observaciones': 'Las observaciones no pueden exceder 2000 caracteres.'})
    if (estado_fisico == 'DANADO' or tipo_movimiento in {'INGRESO_REPARACION', 'SALIDA_REPARACION', 'BAJA'}) and not observaciones:
        raise ValidationError({'observaciones': 'Describa el motivo o trabajo realizado.'})

    try:
        activo = Equipamiento.objects.select_for_update().get(pk=activo_id)
    except (Equipamiento.DoesNotExist, ValueError, TypeError):
        raise ValidationError({'activo_id': 'El activo seleccionado no existe.'})
    antes = _activo_snapshot(activo)
    assigned = activo.usuario_id is not None
    origen_id = colaborador_origen_id
    destino_id = colaborador_destino_id
    needs_origin = (tipo_movimiento in {'DEVOLUCION', 'REASIGNACION'}
                    or (tipo_movimiento == 'INGRESO_REPARACION' and assigned))
    needs_destination = tipo_movimiento in {'ASIGNACION', 'PRESTAMO', 'REASIGNACION', 'CAMBIO'}
    if needs_origin:
        if not assigned or activo.usuario_id != origen_id:
            raise MovimientoConflict('COLABORADOR_ORIGEN_INCORRECTO', 'Indique al custodio actual del activo.')
    elif origen_id is not None:
        raise ValidationError({'colaborador_origen_id': 'Este movimiento no admite colaborador de origen.'})
    if needs_destination:
        if destino_id is None:
            raise ValidationError({'colaborador_destino_id': 'Seleccione el colaborador que recibe.'})
        if origen_id == destino_id:
            raise ValidationError({'colaborador_destino_id': 'Seleccione un colaborador distinto del custodio actual.'})
    elif destino_id is not None:
        raise ValidationError({'colaborador_destino_id': 'Este movimiento no admite colaborador de destino.'})

    if tipo_movimiento in {'ASIGNACION', 'PRESTAMO', 'CAMBIO'}:
        if assigned or activo.estado != 'STOCK':
            raise MovimientoConflict('ACTIVO_NO_DISPONIBLE', 'El activo no está disponible para entrega.')
        estado_resultante = 'PRESTAMO' if tipo_movimiento == 'PRESTAMO' else 'ASIGNADO'
    elif tipo_movimiento == 'DEVOLUCION':
        if activo.estado not in {'ASIGNADO', 'PRESTAMO', 'MANTENCION'}:
            raise MovimientoConflict('ACTIVO_SIN_ASIGNACION', 'El activo no tiene una asignación vigente.')
        estado_resultante = estado_operativo_resultante or 'STOCK'
        if estado_resultante not in {'STOCK', 'MANTENCION'}:
            raise ValidationError({'estado_operativo_resultante': 'La devolución debe quedar disponible o en reparación.'})
    elif tipo_movimiento == 'REASIGNACION':
        if activo.estado not in {'ASIGNADO', 'PRESTAMO'}:
            raise MovimientoConflict('ACTIVO_NO_REASIGNABLE', 'El activo no tiene una asignación transferible.')
        estado_resultante = 'ASIGNADO'
    elif tipo_movimiento == 'INGRESO_REPARACION':
        if activo.estado not in ({'ASIGNADO', 'PRESTAMO'} if assigned else {'STOCK'}):
            raise MovimientoConflict('ACTIVO_NO_REPARABLE', 'El activo debe estar disponible o asignado para ingresar a reparación.')
        estado_resultante = 'MANTENCION'
    elif tipo_movimiento == 'SALIDA_REPARACION':
        if assigned or activo.estado != 'MANTENCION':
            raise MovimientoConflict('ACTIVO_NO_EN_REPARACION', 'El activo debe estar en reparación y sin custodio.')
        estado_resultante = 'STOCK'
    else:
        if assigned or activo.estado != 'STOCK':
            raise MovimientoConflict('ACTIVO_NO_DABLE_DE_BAJA', 'Devuelva el activo y cierre su reparación antes de darlo de baja.')
        estado_resultante = 'BAJA'
    if estado_operativo_resultante not in (None, '', estado_resultante):
        raise ValidationError({'estado_operativo_resultante': 'El estado resultante no corresponde al movimiento.'})

    people_ids = {pk for pk in (origen_id, destino_id) if pk is not None}
    people = {person.pk: person for person in Usuario.objects.select_for_update().select_related(
        'departamento', 'subarea').filter(pk__in=people_ids).order_by('pk')}
    origen = people.get(origen_id)
    destino = people.get(destino_id)
    if needs_origin and origen is None:
        raise ValidationError({'colaborador_origen_id': 'El custodio actual no existe.'})
    if needs_destination:
        if destino is None:
            raise ValidationError({'colaborador_destino_id': 'Seleccione un colaborador válido.'})
        if destino.estado != 'ACTIVO':
            raise MovimientoConflict('COLABORADOR_INACTIVO', 'Solo se pueden asignar activos a colaboradores activos.')
        if not destino.rut:
            raise ValidationError({'colaborador_destino_id': 'Complete el RUT del colaborador antes de emitir un acta.'})
    accesorios = _validar_accesorios(
        accesorios_detalle, activo=activo,
        devolucion=tipo_movimiento in {'DEVOLUCION', 'REASIGNACION'} or
                   (tipo_movimiento == 'INGRESO_REPARACION' and assigned),
        exigir_maestro=tipo_movimiento in {'ASIGNACION', 'PRESTAMO', 'CAMBIO'},
    )
    colaborador = destino or origen
    momento = timezone.now()
    actor = usuario_ti.get_username()
    token = set_current_audit_user(usuario_ti)
    try:
        activo.usuario = destino
        activo.estado = estado_resultante
        activo.estado_fisico = estado_fisico
        activo.ubicacion_actual = ubicacion_destino
        activo.fecha_asignacion = timezone.localdate(momento) if destino else None
        activo.save()
    finally:
        reset_current_audit_user(token)
    despues = _activo_snapshot(activo)
    folio = generar_siguiente_folio(anio=timezone.localdate(momento).year)
    anio, correlativo = (int(part) for part in folio.split('-')[1:])
    documento = {
        'schema_version': 1,
        'folio': folio,
        'fecha_emision': momento.isoformat(),
        'tipo_movimiento': tipo_movimiento,
        'operacion_id': str(operacion_id) if operacion_id else None,
        'colaborador': _colaborador_snapshot(colaborador),
        'colaborador_origen': _colaborador_snapshot(origen),
        'colaborador_destino': _colaborador_snapshot(destino),
        'usuario_ti': {'id': usuario_ti.pk, 'nombre': usuario_ti.get_full_name() or actor, 'username': actor},
        'activo': deepcopy(despues),
        'ubicacion_origen': antes['ubicacion_actual'],
        'ubicacion_destino': ubicacion_destino,
        'estado_fisico': estado_fisico,
        'estado_operativo_resultante': estado_resultante,
        'accesorios': accesorios,
        'observaciones': observaciones,
    }
    if qr_base_url:
        documento['qr_url'] = f"{qr_base_url.rstrip('/')}/qr/a/{activo.token_qr}"
    pdf_buffer = generar_acta_custodia_pdf(documento)
    pdf_bytes = pdf_buffer.getvalue() if hasattr(pdf_buffer, 'getvalue') else bytes(pdf_buffer)
    if not pdf_bytes.startswith(b'%PDF-'):
        raise ValidationError('No fue posible generar un documento PDF válido.')
    acta = ActaEntrega.objects.create(
        folio=folio, anio=anio, numero_correlativo=correlativo,
        tipo_movimiento=tipo_movimiento, colaborador=colaborador,
        usuario_ti=usuario_ti, estado='GENERADA', fecha_emision=momento,
        observaciones=observaciones, snapshot_documento=documento,
        documento_pdf=pdf_bytes, hash_verificacion=hashlib.sha256(pdf_bytes).hexdigest(),
    )
    snapshot = {
        'schema_version': 1,
        'fecha_movimiento': momento.isoformat(),
        'operacion_id': str(operacion_id) if operacion_id else None,
        'antes': antes,
        'despues': despues,
        'colaborador_origen': _colaborador_snapshot(origen),
        'colaborador_destino': _colaborador_snapshot(destino),
        'documento': deepcopy(documento),
    }
    movimiento = MovimientoActivo.objects.create(
        activo=activo, acta=acta, tipo_movimiento=tipo_movimiento, operacion_id=operacion_id,
        fecha_movimiento=momento, colaborador_origen=origen,
        colaborador_destino=destino, ubicacion_origen=antes['ubicacion_actual'],
        ubicacion_destino=ubicacion_destino, estado_fisico=estado_fisico,
        estado_operativo_resultante=estado_resultante, accesorios_detalle=accesorios,
        observaciones=observaciones, ejecutado_por=actor, usuario_ti=usuario_ti,
        snapshot=snapshot,
    )
    SecurityAuditLog.objects.create(
        event=f'{tipo_movimiento}_ACTIVO', actor=actor, module='ACTIVOS_ITAM',
        object_id_text=str(activo.pk), success=True, ip_address=get_request_ip(request),
        detail=json.dumps({'movimiento_id': movimiento.pk, 'folio': folio, **snapshot}, ensure_ascii=False),
    )
    return movimiento
