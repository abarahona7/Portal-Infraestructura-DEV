"""Prueba reversible en MySQL DEV: ejecutar `python manage.py shell < scripts/validar_itam_transaccional.py`."""
# Todos los datos de prueba se crean dentro de una transacción que siempre se revierte.
import uuid
import hashlib
from django.contrib.auth.models import Group, User
from django.db import transaction
from rest_framework.test import APIClient
from core.models import Departamento, Usuario, Equipamiento, MovimientoActivo, ActaEntrega, SecurityAuditLog

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    department = Departamento.objects.create(nombre=f'Prueba ITAM {suffix}')
    person = Usuario.objects.create(nombre_completo=f'Prueba ITAM {suffix}',
        usuario_red=f'itam.{suffix}', correo_corp=f'itam.{suffix}@example.com',
        departamento=department, rut='12.345.678-5')
    operator = User.objects.create_user(username=f'itam_op_{suffix}', password='temporary-only')
    operator.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    asset = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='T14',
        numero_serie=f'ITAM-{suffix}', estado='STOCK', accesorios='Cargador, Mouse')
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=operator)
    first = client.post('/api/movimientos/', {'tipo_movimiento': 'ASIGNACION',
        'activo_id': asset.pk, 'colaborador_destino_id': person.pk,
        'ubicacion_destino': 'Oficina', 'estado_fisico': 'USADO',
        'accesorios_detalle': [{'nombre':'Cargador','entregado':True},
                              {'nombre':'Mouse','entregado':True}]}, format='json')
    assert first.status_code == 201, (first.status_code, first.data)
    assert first.data['acta']['folio'].startswith('ATI-'), first.data
    asset.refresh_from_db()
    qr_path = f'/api/activos/qr/{asset.token_qr}/'
    qr_detail = client.get(qr_path)
    assert qr_detail.status_code == 200, (qr_detail.status_code, getattr(qr_detail, 'data', None))
    assert qr_detail.data['activo']['usuario_nombre'] == person.nombre_completo
    assert qr_detail.data['qr_url'].endswith(f'/qr/a/{asset.token_qr}')
    assert 'rut' not in qr_detail.data['activo']
    qr_image = client.get(f'{qr_path}imagen/')
    assert qr_image.status_code == 200 and qr_image['Content-Type'].startswith('image/svg+xml')
    assert b'<svg' in qr_image.content and person.nombre_completo.encode() not in qr_image.content
    anonymous = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    assert anonymous.get(qr_path).status_code in (401, 403)
    assert anonymous.get(f'{qr_path}imagen/').status_code in (401, 403)
    assert client.get(f'/api/activos/qr/{uuid.uuid4()}/').status_code == 404
    direct = client.patch(f'/api/equipos/{asset.pk}/', {'usuario': None}, format='json')
    assert direct.status_code == 400, (direct.status_code, getattr(direct, 'data', None))
    inactive = client.patch(f'/api/usuarios/{person.pk}/', {'estado': 'BAJA'}, format='json')
    assert inactive.status_code == 400, (inactive.status_code, getattr(inactive, 'data', None))
    pdf = client.get(f"/api/actas/{first.data['acta']['id']}/pdf/")
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF-'), pdf.status_code
    assert hashlib.sha256(pdf.content).hexdigest() == first.data['acta']['hash_verificacion']
    double = client.post('/api/movimientos/', {'tipo_movimiento': 'ASIGNACION',
        'activo_id': asset.pk, 'colaborador_destino_id': person.pk,
        'ubicacion_destino': 'Oficina', 'estado_fisico': 'USADO',
        'accesorios_detalle': []}, format='json')
    assert double.status_code == 409, (double.status_code, double.data)
    missing = client.post('/api/movimientos/', {'tipo_movimiento': 'DEVOLUCION',
        'activo_id': asset.pk, 'colaborador_origen_id': person.pk,
        'ubicacion_destino': 'Bodega TI', 'estado_fisico': 'USADO',
        'accesorios_detalle': [{'nombre':'Cargador','entregado':True}]}, format='json')
    assert missing.status_code == 400, (missing.status_code, missing.data)
    returned = client.post('/api/movimientos/', {'tipo_movimiento': 'DEVOLUCION',
        'activo_id': asset.pk, 'colaborador_origen_id': person.pk,
        'ubicacion_destino': 'Bodega TI', 'estado_fisico': 'USADO',
        'accesorios_detalle': [{'nombre':'Cargador','entregado':True},
                              {'nombre':'Mouse','entregado':False,'nota':'Extraviado'}]}, format='json')
    assert returned.status_code == 201, (returned.status_code, returned.data)
    assert returned.data['acta']['folio'] != first.data['acta']['folio']
    assert client.delete(f"/api/movimientos/{first.data['id']}/").status_code == 403
    asset.refresh_from_db()
    assert asset.usuario_id is None and asset.estado == 'STOCK'
    history = client.get(f'/api/movimientos/?activo_id={asset.pk}')
    assert history.status_code == 200 and history.data['count'] == 2
    assert MovimientoActivo.objects.filter(activo=asset).count() == 2
    assert ActaEntrega.objects.filter(movimientos__activo=asset).count() == 2
    assert SecurityAuditLog.objects.filter(module='ACTIVOS_ITAM', object_id_text=str(asset.pk)).count() == 2
    print('ITAM transacción: asignación/devolución/folio/PDF/QR/historial/conflicto/accesorios/auditoría OK')
    print(f'Folios temporales: {first.data["acta"]["folio"]}, {returned.data["acta"]["folio"]}')
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie=f'ITAM-{suffix}').exists()
print('Rollback verificado: sin registros de prueba persistidos')
