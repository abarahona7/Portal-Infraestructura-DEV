"""Ejecutar con `.venv/bin/python manage.py shell < scripts/validar_actas_estado_transaccional.py`."""
import hashlib
import uuid

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from rest_framework.test import APIClient

from core.models import ActaEntrega, ActaEstadoEvento, Departamento, Equipamiento, Usuario

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    department = Departamento.objects.create(nombre=f'Validación actas {suffix}')
    person = Usuario.objects.create(nombre_completo='Persona Actas', usuario_red=f'actas.{suffix}',
        correo_corp=f'actas.{suffix}@example.com', departamento=department, rut='11.111.111-1')
    operator = User.objects.create_user(username=f'actas_op_{suffix}', password='temporary-only')
    operator.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    admin = User.objects.create_user(username=f'actas_admin_{suffix}', password='temporary-only')
    admin.groups.add(Group.objects.get_or_create(name='Administrador')[0])
    asset = Equipamiento.objects.create(tipo='Notebook', marca='Validación', modelo='Actas',
        numero_serie=f'ACTAS-{suffix}', estado='STOCK', accesorios='Cargador')
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=operator)
    issued = client.post('/api/movimientos/', {
        'tipo_movimiento': 'ASIGNACION', 'activo_id': asset.pk,
        'colaborador_destino_id': person.pk, 'ubicacion_destino': 'Oficina',
        'estado_fisico': 'USADO', 'accesorios_detalle': [{'nombre': 'Cargador', 'entregado': True}],
    }, format='json')
    assert issued.status_code == 201, (issued.status_code, issued.data)
    acta_id = issued.data['acta']['id']
    original = client.get(f'/api/actas/{acta_id}/pdf/')
    assert original.status_code == 200
    original_bytes = original.content
    original_hash = hashlib.sha256(original_bytes).hexdigest()
    assert original_hash == issued.data['acta']['hash_verificacion']
    endpoint = f'/api/actas/{acta_id}/estado/'
    assert client.post(endpoint, {'estado_nuevo': 'CERRADA'}, format='json').status_code == 400
    assert client.post(endpoint, {'estado_nuevo': 'ANULADA', 'motivo': 'Prueba'}, format='json').status_code == 403
    pending = client.post(endpoint, {'estado_nuevo': 'PENDIENTE_FIRMA'}, format='json')
    assert pending.status_code == 200 and pending.data['estado'] == 'PENDIENTE_FIRMA', pending.data
    assert client.post(endpoint, {'estado_nuevo': 'PENDIENTE_FIRMA'}, format='json').status_code == 400
    assert client.post(endpoint, {'estado_nuevo': 'FIRMADA'}, format='json').status_code == 400
    invalid = SimpleUploadedFile('mal.pdf', b'No es PDF', content_type='application/pdf')
    assert client.post(endpoint, {'estado_nuevo': 'FIRMADA', 'archivo_firmado': invalid}).status_code == 400
    signed_file = SimpleUploadedFile('copia.pdf', original_bytes, content_type='application/pdf')
    signed = client.post(endpoint, {'estado_nuevo': 'FIRMADA', 'archivo_firmado': signed_file})
    assert signed.status_code == 200 and signed.data['estado'] == 'FIRMADA', (signed.status_code, signed.data)
    assert signed.data['tiene_copia_firmada']
    assert client.get(f'/api/actas/{acta_id}/firmada/').content == original_bytes
    closed = client.post(endpoint, {'estado_nuevo': 'CERRADA'}, format='json')
    assert closed.status_code == 200 and closed.data['estado'] == 'CERRADA' and closed.data['fecha_cierre']
    history = client.get(f'/api/actas/{acta_id}/eventos/')
    assert history.status_code == 200 and [event['estado_nuevo'] for event in history.data] == ['CERRADA', 'FIRMADA', 'PENDIENTE_FIRMA']
    assert history.data[1]['hash_copia_firmada'] == original_hash
    assert client.get(f'/api/movimientos/{issued.data["id"]}/').data['acta']['estado'] == 'CERRADA'
    assert client.get(f'/api/actas/{acta_id}/pdf/').content == original_bytes
    client.force_authenticate(user=admin)
    assert client.post(endpoint, {'estado_nuevo': 'ANULADA'}, format='json').status_code == 400
    annulled = client.post(endpoint, {'estado_nuevo': 'ANULADA', 'motivo': 'Acta invalidada en prueba'}, format='json')
    assert annulled.status_code == 200 and annulled.data['estado'] == 'ANULADA', annulled.data
    assert annulled.data['fecha_cierre'] and annulled.data['tiene_copia_firmada']
    assert client.post(endpoint, {'estado_nuevo': 'ANULADA', 'motivo': 'Otra vez'}, format='json').status_code == 400
    assert client.get(f'/api/actas/{acta_id}/pdf/').content == original_bytes
    assert client.get(f'/api/actas/{acta_id}/firmada/').content == original_bytes
    stored = ActaEntrega.objects.get(pk=acta_id)
    assert stored.estado == 'GENERADA' and stored.hash_verificacion == original_hash
    assert ActaEstadoEvento.objects.filter(acta_id=acta_id).count() == 4
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie=f'ACTAS-{suffix}').exists()
print('Actas: transiciones, permisos, copia firmada, PDF original e historial inmutable OK; rollback completo')
