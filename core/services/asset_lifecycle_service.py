"""Atomic asset assignments/returns and their immutable documentary evidence."""

from copy import deepcopy
import hashlib
import ipaddress
import json
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.audit import reset_current_audit_user, set_current_audit_user
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
    ultimo = activo.movimientos.filter(tipo_movimiento='ASIGNACION').first()
    if ultimo is not None:
        return [item['nombre'] for item in ultimo.accesorios_detalle if item.get('entregado')]
    return list(dict.fromkeys(
        _text(nombre) for nombre in re.split(r'[,;\n]+', activo.accesorios or '') if _text(nombre)
    ))


def _validar_accesorios(items, *, activo, devolucion):
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
    if not devolucion and not activo.movimientos.exists():
        missing = [name for name in re.split(r'[,;\n]+', activo.accesorios or '')
                   if _text(name) and _text(name).casefold() not in seen]
        if missing:
            raise ValidationError({'accesorios_detalle': 'Revise los accesorios registrados en el activo: ' + ', '.join(missing) + '.'})
    if devolucion:
        missing = [name for name in accesorios_requeridos(activo) if name.casefold() not in seen]
        if missing:
            raise ValidationError({'accesorios_detalle': 'Revise todos los accesorios entregados: ' + ', '.join(missing) + '.'})
    return normalized


def _client_ip(request):
    if request is None:
        return None
    # REMOTE_ADDR is supplied by the server. Do not trust arbitrary forwarded headers.
    raw = request.META.get('REMOTE_ADDR')
    try:
        return str(ipaddress.ip_address(raw)) if raw else None
    except ValueError:
        return None


@transaction.atomic
def registrar_movimiento(*, tipo_movimiento, activo_id, usuario_ti,
                         colaborador_destino_id=None, colaborador_origen_id=None,
                         ubicacion_destino, estado_fisico='USADO',
                         estado_operativo_resultante=None, accesorios_detalle=None,
                         observaciones='', request=None, qr_base_url=None):
    """Persist a movement, current asset state, acta/PDF and audit in one commit.

    The caller authorizes the operator and passes the authenticated user. Public
    entry points must never accept that identity from request data.
    """
    if tipo_movimiento not in {'ASIGNACION', 'DEVOLUCION'}:
        raise ValidationError({'tipo_movimiento': 'En esta fase solo se admiten asignaciones y devoluciones.'})
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
    if estado_fisico == 'DANADO' and not observaciones:
        raise ValidationError({'observaciones': 'Describa el daño observado en el activo.'})

    try:
        activo = Equipamiento.objects.select_for_update().get(pk=activo_id)
    except (Equipamiento.DoesNotExist, ValueError, TypeError):
        raise ValidationError({'activo_id': 'El activo seleccionado no existe.'})
    antes = _activo_snapshot(activo)
    origen = None
    destino = None
    devolucion = tipo_movimiento == 'DEVOLUCION'
    if not devolucion:
        if activo.usuario_id is not None or activo.estado != 'STOCK':
            raise MovimientoConflict('ACTIVO_NO_DISPONIBLE', 'El activo no está disponible. Registre primero su devolución.')
        if colaborador_origen_id is not None:
            raise ValidationError({'colaborador_origen_id': 'Una asignación no debe indicar colaborador de origen.'})
        try:
            destino = Usuario.objects.select_for_update().select_related('departamento', 'subarea').get(pk=colaborador_destino_id)
        except (Usuario.DoesNotExist, ValueError, TypeError):
            raise ValidationError({'colaborador_destino_id': 'Seleccione un colaborador válido.'})
        if destino.estado != 'ACTIVO':
            raise MovimientoConflict('COLABORADOR_INACTIVO', 'Solo se pueden asignar activos a colaboradores activos.')
        if not destino.rut:
            raise ValidationError({'colaborador_destino_id': 'Complete el RUT del colaborador antes de emitir un acta.'})
        if estado_operativo_resultante not in (None, '', 'ASIGNADO'):
            raise ValidationError({'estado_operativo_resultante': 'Una asignación debe resultar en estado ASIGNADO.'})
        estado_resultante = 'ASIGNADO'
    else:
        if activo.usuario_id is None or activo.estado not in {'ASIGNADO', 'PRESTAMO', 'MANTENCION'}:
            raise MovimientoConflict('ACTIVO_SIN_ASIGNACION', 'El activo no tiene una asignación vigente que pueda devolverse.')
        if colaborador_destino_id is not None:
            raise ValidationError({'colaborador_destino_id': 'Una devolución no debe indicar colaborador de destino.'})
        if colaborador_origen_id is None:
            raise ValidationError({'colaborador_origen_id': 'Indique el colaborador que devuelve el activo.'})
        if activo.usuario_id != colaborador_origen_id:
            raise MovimientoConflict('COLABORADOR_ORIGEN_INCORRECTO', 'El activo no está asignado al colaborador indicado.')
        origen = Usuario.objects.select_for_update().select_related('departamento', 'subarea').get(pk=activo.usuario_id)
        estado_resultante = estado_operativo_resultante or 'STOCK'
        if estado_resultante not in {'STOCK', 'MANTENCION'}:
            raise ValidationError({'estado_operativo_resultante': 'Una devolución puede quedar en STOCK o MANTENCION.'})
    accesorios = _validar_accesorios(accesorios_detalle, activo=activo, devolucion=devolucion)
    colaborador = origen if devolucion else destino
    momento = timezone.now()
    actor = usuario_ti.get_username()
    token = set_current_audit_user(usuario_ti)
    try:
        activo.usuario = destino
        activo.estado = estado_resultante
        activo.estado_fisico = estado_fisico
        activo.ubicacion_actual = ubicacion_destino
        activo.fecha_asignacion = None if devolucion else timezone.localdate(momento)
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
        'colaborador': _colaborador_snapshot(colaborador),
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
        'antes': antes,
        'despues': despues,
        'colaborador_origen': _colaborador_snapshot(origen),
        'colaborador_destino': _colaborador_snapshot(destino),
        'documento': deepcopy(documento),
    }
    movimiento = MovimientoActivo.objects.create(
        activo=activo, acta=acta, tipo_movimiento=tipo_movimiento,
        fecha_movimiento=momento, colaborador_origen=origen,
        colaborador_destino=destino, ubicacion_origen=antes['ubicacion_actual'],
        ubicacion_destino=ubicacion_destino, estado_fisico=estado_fisico,
        estado_operativo_resultante=estado_resultante, accesorios_detalle=accesorios,
        observaciones=observaciones, ejecutado_por=actor, usuario_ti=usuario_ti,
        snapshot=snapshot,
    )
    SecurityAuditLog.objects.create(
        event=f'{tipo_movimiento}_ACTIVO', actor=actor, module='ACTIVOS_ITAM',
        object_id_text=str(activo.pk), success=True, ip_address=_client_ip(request),
        detail=json.dumps({'movimiento_id': movimiento.pk, 'folio': folio, **snapshot}, ensure_ascii=False),
    )
    return movimiento
