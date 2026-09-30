"""Periodos de custodia derivados de movimientos inmutables y asignaciones legadas."""
from django.db.models import Q

from core.models import Equipamiento, MovimientoActivo

ENTRADAS = {'ASIGNACION', 'PRESTAMO', 'REASIGNACION', 'CAMBIO'}
SALIDAS = {'DEVOLUCION', 'REASIGNACION', 'INGRESO_REPARACION'}
CAMPOS_ACTIVO = ('tipo', 'marca', 'modelo', 'numero_serie', 'af')


def _activo(snapshot, equipo):
    return {campo: snapshot.get(campo) for campo in CAMPOS_ACTIVO} | {'id': equipo.pk}


def _periodo_legado(equipo, *, fecha=None, snapshot=None):
    return {
        'activo': _activo(snapshot or {}, equipo),
        'fecha_asignacion': fecha,
        'fecha_devolucion': None,
        'tipo_entrega': 'LEGADO',
        'tipo_salida': None,
        'folio_entrega': None,
        'folio_salida': None,
        'acta_entrega_id': None,
        'acta_salida_id': None,
        'estado': 'SIN_CIERRE_REGISTRADO',
    }


def periodos_custodia(colaborador_id):
    """Empareja entregas y salidas por activo sin reconstruir eventos inexistentes."""
    movimientos = MovimientoActivo.objects.filter(
        Q(colaborador_origen_id=colaborador_id) | Q(colaborador_destino_id=colaborador_id)
    ).select_related('activo', 'acta').defer('acta__documento_pdf').order_by('fecha_movimiento', 'pk')
    periodos = []
    abiertos = {}
    for movimiento in movimientos:
        activo_id = movimiento.activo_id
        antes = (movimiento.snapshot or {}).get('antes') or {}
        despues = (movimiento.snapshot or {}).get('despues') or {}
        fecha = movimiento.fecha_movimiento.isoformat()
        if movimiento.colaborador_origen_id == colaborador_id and movimiento.tipo_movimiento in SALIDAS:
            periodo = abiertos.pop(activo_id, None)
            if periodo is None:
                periodo = _periodo_legado(
                    movimiento.activo, fecha=antes.get('fecha_asignacion'), snapshot=antes,
                )
                periodos.append(periodo)
            periodo.update({
                'fecha_devolucion': fecha,
                'tipo_salida': movimiento.tipo_movimiento,
                'folio_salida': movimiento.acta.folio if movimiento.acta_id else None,
                'acta_salida_id': movimiento.acta_id,
                'estado': 'FINALIZADO',
            })
        if movimiento.colaborador_destino_id == colaborador_id and movimiento.tipo_movimiento in ENTRADAS:
            periodo = {
                'activo': _activo(despues, movimiento.activo),
                'fecha_asignacion': fecha,
                'fecha_devolucion': None,
                'tipo_entrega': movimiento.tipo_movimiento,
                'tipo_salida': None,
                'folio_entrega': movimiento.acta.folio if movimiento.acta_id else None,
                'folio_salida': None,
                'acta_entrega_id': movimiento.acta_id,
                'acta_salida_id': None,
                'estado': 'SIN_CIERRE_REGISTRADO',
            }
            periodos.append(periodo)
            abiertos[activo_id] = periodo

    vigentes = Equipamiento.objects.filter(usuario_id=colaborador_id).only(
        'id', *CAMPOS_ACTIVO, 'fecha_asignacion'
    )
    for equipo in vigentes:
        periodo = abiertos.get(equipo.pk)
        if periodo is None:
            periodo = _periodo_legado(
                equipo,
                fecha=equipo.fecha_asignacion.isoformat() if equipo.fecha_asignacion else None,
                snapshot={campo: getattr(equipo, campo) for campo in CAMPOS_ACTIVO},
            )
            periodos.append(periodo)
        periodo['estado'] = 'VIGENTE'

    return sorted(periodos, key=lambda item: item['fecha_devolucion'] or item['fecha_asignacion'] or '', reverse=True)
