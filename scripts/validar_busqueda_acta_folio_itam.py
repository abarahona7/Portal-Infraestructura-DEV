"""Ejecutar con `python manage.py shell < scripts/validar_busqueda_acta_folio_itam.py`."""
import uuid

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.models import ActaEntrega, MovimientoActivo

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    operator = User.objects.create_user(username=f'folio_lookup_{suffix}', password='temporary-only')
    operator.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=operator)
    created = client.post('/api/equipos/', {
        'tipo': 'Monitor', 'marca': 'Prueba', 'modelo': 'Consulta de folio',
        'numero_serie': f'FL-{suffix}', 'estado': 'STOCK',
        'estado_fisico': 'USADO', 'ubicacion_actual': 'Bodega TI',
    }, format='json')
    assert created.status_code == 201, (created.status_code, created.data)
    movement = MovimientoActivo.objects.get(activo_id=created.data['id'], tipo_movimiento='ALTA')
    acta = movement.acta
    folio = acta.folio
    found = client.get('/api/actas/', {'folio': folio.lower()})
    assert found.status_code == 200, (found.status_code, found.data)
    assert found.data['count'] == 1 and found.data['results'][0]['id'] == acta.pk
    assert found.data['results'][0]['folio'] == folio
    assert found.data['results'][0]['estado'] == 'GENERADA'
    assert found['Cache-Control'] == 'no-store, private'
    original = client.get(f'/api/actas/{acta.pk}/pdf/')
    assert original.status_code == 200 and original.content.startswith(b'%PDF-')
    pending = client.post(f'/api/actas/{acta.pk}/estado/', {'estado_nuevo': 'PENDIENTE_FIRMA'}, format='json')
    assert pending.status_code == 200, (pending.status_code, pending.data)
    updated = client.get('/api/actas/', {'folio': folio})
    assert updated.status_code == 200 and updated.data['results'][0]['estado'] == 'PENDIENTE_FIRMA'
    archive_pending = client.get('/api/actas/', {
        'folio': folio, 'estado': 'PENDIENTE_FIRMA', 'tipo_movimiento': 'ALTA', 'page_size': 1,
    })
    assert archive_pending.status_code == 200 and archive_pending.data['count'] == 1
    assert archive_pending.data['results'][0]['id'] == acta.pk
    archive_old = client.get('/api/actas/', {'folio': folio, 'estado': 'GENERADA'})
    assert archive_old.status_code == 200 and archive_old.data['count'] == 0
    archive_wrong_type = client.get('/api/actas/', {'folio': folio, 'tipo_movimiento': 'BAJA'})
    assert archive_wrong_type.status_code == 200 and archive_wrong_type.data['count'] == 0
    assert client.get('/api/actas/', {'estado': 'INVENTADO'}).status_code == 400
    assert client.get('/api/actas/', {'tipo_movimiento': 'INVENTADO'}).status_code == 400
    signed_file = SimpleUploadedFile('copia.pdf', original.content, content_type='application/pdf')
    signed = client.post(f'/api/actas/{acta.pk}/estado/', {
        'estado_nuevo': 'FIRMADA', 'archivo_firmado': signed_file,
    }, format='multipart')
    assert signed.status_code == 200, (signed.status_code, signed.data)
    assert client.get('/api/actas/', {'folio': folio, 'estado': 'FIRMADA'}).data['count'] == 1
    closed = client.post(f'/api/actas/{acta.pk}/estado/', {'estado_nuevo': 'CERRADA'}, format='json')
    assert closed.status_code == 200, (closed.status_code, closed.data)
    archive_closed = client.get('/api/actas/', {'folio': folio, 'estado': 'CERRADA'})
    assert archive_closed.status_code == 200 and archive_closed.data['count'] == 1
    assert archive_closed.data['results'][0]['tiene_copia_firmada'] is True
    assert client.get('/api/actas/', {'folio': folio, 'estado': 'FIRMADA'}).data['count'] == 0
    assert client.get(f'/api/actas/{acta.pk}/firmada/').status_code == 200
    invalid = client.get('/api/actas/', {'folio': 'ATI-invalido'})
    assert invalid.status_code == 400 and 'folio' in invalid.data
    empty = client.get('/api/actas/', {'folio': 'ATI-2000-000000'})
    assert empty.status_code == 200 and empty.data['count'] == 0
    viewer = User.objects.create_user(username=f'folio_view_{suffix}', password='temporary-only')
    viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
    client.force_authenticate(user=viewer)
    assert client.get('/api/actas/', {'folio': folio}).status_code == 403
    anonymous = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    assert anonymous.get('/api/actas/', {'folio': folio}).status_code in (401, 403)
    transaction.set_rollback(True)
assert not ActaEntrega.objects.filter(folio=folio).exists()
print('Archivo ITAM: folio, filtros de estado vigente/tipo, PDF y permisos OK; rollback confirmado')
