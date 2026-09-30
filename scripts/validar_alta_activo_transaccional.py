"""Ejecutar con `.venv/bin/python manage.py shell < scripts/validar_alta_activo_transaccional.py`."""
import hashlib
import logging
import uuid
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.db import transaction
from rest_framework.test import APIClient

from core.models import ActaEntrega, Equipamiento, FolioContador, MovimientoActivo, SecurityAuditLog
from core.services.asset_lifecycle_service import MovimientoConflict, registrar_movimiento

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    actor = User.objects.create_user(username=f'alta_op_{suffix}', password='temporal')
    actor.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=actor)
    payload = {'tipo': 'Monitor', 'marca': 'Prueba', 'modelo': 'Alta', 'estado': 'STOCK',
               'estado_fisico': 'NUEVO', 'ubicacion_actual': 'Bodega TI',
               'accesorios': 'Cable HDMI', 'numero_serie': f'ALTA-{suffix}'}
    created = client.post('/api/equipos/', payload, format='json')
    assert created.status_code == 201, (created.status_code, created.data)
    asset = Equipamiento.objects.get(pk=created.data['id'])
    movement = MovimientoActivo.objects.get(activo=asset)
    acta = ActaEntrega.objects.get(pk=movement.acta_id)
    assert asset.estado == 'STOCK' and asset.usuario_id is None
    assert movement.tipo_movimiento == acta.tipo_movimiento == 'ALTA'
    assert movement.snapshot['antes'] is None and movement.snapshot['despues']['id'] == asset.pk
    assert acta.snapshot_documento['activo']['accesorios'] == 'Cable HDMI'
    assert acta.folio.startswith('ATI-') and bytes(acta.documento_pdf).startswith(b'%PDF-')
    assert hashlib.sha256(bytes(acta.documento_pdf)).hexdigest() == acta.hash_verificacion
    assert SecurityAuditLog.objects.filter(module='ACTIVOS_ITAM', event='ALTA_ACTIVO',
                                           object_id_text=str(asset.pk)).exists()
    try:
        registrar_movimiento(tipo_movimiento='ALTA', activo_id=asset.pk, usuario_ti=actor,
                             ubicacion_destino='Bodega TI', estado_fisico='NUEVO')
    except MovimientoConflict as error:
        assert error.codigo == 'ALTA_YA_REGISTRADA'
    else:
        raise AssertionError('No debe duplicarse el alta del mismo activo.')
    call_command('validar_integridad_itam', stdout=StringIO())
    before = (Equipamiento.objects.count(), MovimientoActivo.objects.count(),
              ActaEntrega.objects.count(), SecurityAuditLog.objects.filter(module='ACTIVOS_ITAM', event='ALTA_ACTIVO').count(),
              FolioContador.objects.get(anio=acta.anio, tipo_documento='ATI').ultimo_folio)
    client.raise_request_exception = False
    previous_logging = logging.root.manager.disable
    try:
        logging.disable(logging.CRITICAL)
        with patch('core.services.asset_lifecycle_service.generar_acta_custodia_pdf', side_effect=RuntimeError('PDF no disponible')):
            failed = client.post('/api/equipos/', {**payload, 'numero_serie': f'FAL-{suffix}'}, format='json')
    finally:
        logging.disable(previous_logging)
    assert failed.status_code == 500, failed.status_code
    after = (Equipamiento.objects.count(), MovimientoActivo.objects.count(),
             ActaEntrega.objects.count(), SecurityAuditLog.objects.filter(module='ACTIVOS_ITAM', event='ALTA_ACTIVO').count(),
             FolioContador.objects.get(anio=acta.anio, tipo_documento='ATI').ultimo_folio)
    assert after == before, (before, after)
    assert not Equipamiento.objects.filter(numero_serie=f'FAL-{suffix}').exists()
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie=f'ALTA-{suffix}').exists()
print('Alta: activo, movimiento, acta y folio atómicos; duplicado y falla PDF revertidos')
