"""Ejecutar con `python manage.py shell < scripts/validar_itam_fase2_transaccional.py`."""
import hashlib
import uuid
from io import BytesIO
from unittest.mock import patch
from django.contrib.auth.models import Group, User
from django.db import transaction
from rest_framework.test import APIClient
from core.models import ActaEntrega, Departamento, Equipamiento, MovimientoActivo, Usuario

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    department = Departamento.objects.create(nombre=f'Prueba F2 {suffix}')
    first = Usuario.objects.create(nombre_completo='Persona F2 origen', usuario_red=f'f2a.{suffix}',
        correo_corp=f'f2a.{suffix}@example.com', departamento=department, rut='11.111.111-1')
    second = Usuario.objects.create(nombre_completo='Persona F2 destino', usuario_red=f'f2b.{suffix}',
        correo_corp=f'f2b.{suffix}@example.com', departamento=department, rut='9.876.543-3')
    actor = User.objects.create_user(username=f'f2_op_{suffix}', password='temporary-only')
    actor.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    asset = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='F2',
        numero_serie=f'F2-{suffix}', estado='STOCK', accesorios='Cargador')
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=actor)
    def move(kind, *, asset_id=None, origin=None, destination=None, notes='', accessories=None):
        payload = {'tipo_movimiento': kind, 'activo_id': asset_id or asset.pk,
            'ubicacion_destino': 'Bodega TI', 'estado_fisico': 'USADO',
            'accesorios_detalle': accessories if accessories is not None else [], 'observaciones': notes}
        if origin is not None:
            payload['colaborador_origen_id'] = origin.pk
        if destination is not None:
            payload['colaborador_destino_id'] = destination.pk
        return client.post('/api/movimientos/', payload, format='json')
    checklist = [{'nombre': 'Cargador', 'entregado': True}]
    assigned = move('ASIGNACION', destination=first, accessories=checklist)
    assert assigned.status_code == 201, (assigned.status_code, assigned.data)
    transferred = move('REASIGNACION', origin=first, destination=second, accessories=checklist)
    assert transferred.status_code == 201, (transferred.status_code, transferred.data)
    asset.refresh_from_db()
    assert asset.usuario_id == second.pk and asset.estado == 'ASIGNADO'
    assert transferred.data['colaborador_origen']['id'] == first.pk
    assert transferred.data['colaborador_destino']['id'] == second.pk
    assert move('REASIGNACION', origin=second, destination=second, accessories=checklist).status_code == 400
    assert move('BAJA', notes='Baja prematura').status_code == 409
    repair = move('INGRESO_REPARACION', origin=second, notes='Falla de pantalla', accessories=checklist)
    assert repair.status_code == 201, (repair.status_code, repair.data)
    asset.refresh_from_db()
    assert asset.usuario_id is None and asset.estado == 'MANTENCION'
    assert move('ASIGNACION', destination=first, accessories=checklist).status_code == 409
    assert move('BAJA', notes='Baja prematura').status_code == 409
    returned = move('SALIDA_REPARACION', notes='Pantalla sustituida')
    assert returned.status_code == 201, (returned.status_code, returned.data)
    asset.refresh_from_db()
    assert asset.estado == 'STOCK' and asset.usuario_id is None
    retired = move('BAJA', notes='Obsolescencia técnica')
    assert retired.status_code == 201, (retired.status_code, retired.data)
    asset.refresh_from_db()
    assert asset.estado == 'BAJA' and asset.usuario_id is None
    assert retired.data['acta']['colaborador_id'] is None
    assert str(ActaEntrega.objects.get(pk=retired.data['acta']['id'])).startswith(retired.data['acta']['folio'])
    pdf = client.get(f"/api/actas/{retired.data['acta']['id']}/pdf/")
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF-')
    assert hashlib.sha256(pdf.content).hexdigest() == retired.data['acta']['hash_verificacion']
    assert move('ASIGNACION', destination=first, accessories=checklist).status_code == 409
    assert MovimientoActivo.objects.filter(activo=asset).count() == 5
    assert len({item.acta.folio for item in MovimientoActivo.objects.filter(activo=asset)}) == 5
    assert ActaEntrega.objects.filter(movimientos__activo=asset).count() == 5
    assert client.get(f'/api/movimientos/?colaborador_id={first.pk}').data['count'] == 2
    assert client.get(f'/api/movimientos/?colaborador_id={second.pk}').data['count'] == 2
    spare = Equipamiento.objects.create(tipo='Monitor', marca='Prueba', modelo='F2',
        numero_serie=f'F2-B-{suffix}', estado='STOCK', accesorios='Cable')
    direct_repair = move('INGRESO_REPARACION', asset_id=spare.pk, notes='Falla de imagen')
    assert direct_repair.status_code == 201, (direct_repair.status_code, direct_repair.data)
    assert direct_repair.data['acta']['colaborador_id'] is None
    spare.refresh_from_db()
    assert spare.estado == 'MANTENCION' and spare.usuario_id is None
    with patch('core.services.asset_lifecycle_service.generar_acta_custodia_pdf', return_value=BytesIO(b'INVALIDO')):
        failed = move('SALIDA_REPARACION', asset_id=spare.pk, notes='Revisado')
    assert failed.status_code == 400, (failed.status_code, failed.data)
    spare.refresh_from_db()
    assert spare.estado == 'MANTENCION'
    assert MovimientoActivo.objects.filter(activo=spare).count() == 1
    fixed = move('SALIDA_REPARACION', asset_id=spare.pk, notes='Reparación completada')
    assert fixed.status_code == 201, (fixed.status_code, fixed.data)
    assert int(fixed.data['acta']['folio'][-6:]) == int(direct_repair.data['acta']['folio'][-6:]) + 1
    assert move('ASIGNACION', asset_id=spare.pk, destination=first).status_code == 400
    issued = move('ASIGNACION', asset_id=spare.pk, destination=first,
        accessories=[{'nombre': 'Cable', 'entregado': True}])
    assert issued.status_code == 201, (issued.status_code, issued.data)
    spare.refresh_from_db()
    assert spare.usuario_id == first.pk and spare.estado == 'ASIGNADO'
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie__in=[f'F2-{suffix}', f'F2-B-{suffix}']).exists()
print('ITAM Fase 2: reasignación/reparación/baja/PDF/folio/rollback/conflictos OK')
