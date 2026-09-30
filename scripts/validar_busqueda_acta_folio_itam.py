"""Ejecutar con `python manage.py shell < scripts/validar_busqueda_acta_folio_itam.py`."""
import csv
import io
import uuid
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.asset_api import _comprobar_pdf
from core.models import ActaEntrega, ActaEstadoEvento, MovimientoActivo

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
    issue_date = timezone.localdate(acta.fecha_emision)
    by_date = client.get('/api/actas/', {
        'folio': folio, 'desde': issue_date.isoformat(), 'hasta': issue_date.isoformat(),
    })
    assert by_date.status_code == 200 and by_date.data['count'] == 1
    later = client.get('/api/actas/', {'folio': folio, 'desde': (issue_date + timedelta(days=1)).isoformat()})
    assert later.status_code == 200 and later.data['count'] == 0
    assert client.get('/api/actas/', {'desde': 'ayer'}).status_code == 400
    assert client.get('/api/actas/', {
        'desde': issue_date.isoformat(), 'hasta': (issue_date - timedelta(days=1)).isoformat(),
    }).status_code == 400
    original = client.get(f'/api/actas/{acta.pk}/pdf/')
    assert original.status_code == 200 and original.content.startswith(b'%PDF-')
    initial_integrity = client.get(f'/api/actas/{acta.pk}/integridad/')
    assert initial_integrity.status_code == 200 and initial_integrity.data['original']['coincide'] is True
    assert initial_integrity.data['copia_firmada'] is None
    assert initial_integrity['Cache-Control'] == 'no-store, private'
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
    report = client.get('/api/actas/reporte/', {
        'folio': folio, 'estado': 'CERRADA', 'tipo_movimiento': 'ALTA',
        'desde': issue_date.isoformat(), 'hasta': issue_date.isoformat(),
    })
    assert report.status_code == 200 and report['Cache-Control'] == 'no-store, private'
    assert report['X-Content-Type-Options'] == 'nosniff'
    content = b''.join(report.streaming_content).decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(content), delimiter=';'))
    assert len(rows) == 2 and rows[1][1] == folio and rows[1][4] == 'CERRADA'
    assert rows[1][5] == acta.hash_verificacion
    signed_event = ActaEstadoEvento.objects.get(acta=acta, estado_nuevo='FIRMADA')
    assert rows[1][6] == signed_event.hash_copia_firmada
    verified = client.get(f'/api/actas/{acta.pk}/integridad/')
    assert verified.status_code == 200 and verified.data['folio'] == folio
    assert verified.data['original']['coincide'] is True
    assert verified.data['copia_firmada']['coincide'] is True
    assert verified.data['original']['sha256_registrado'] == acta.hash_verificacion
    assert verified.data['copia_firmada']['sha256_registrado'] == signed_event.hash_copia_firmada
    assert '%PDF-' not in str(verified.data)
    assert _comprobar_pdf(b'%PDF-corrupto', acta.hash_verificacion)['coincide'] is False
    assert _comprobar_pdf(b'%PDF-corrupto', signed_event.hash_copia_firmada)['coincide'] is False
    assert _comprobar_pdf(None, acta.hash_verificacion)['coincide'] is False
    assert _comprobar_pdf(original.content, acta.hash_verificacion)['coincide'] is True

    assert 'snapshot' not in content.lower() and '%PDF-' not in content
    empty_report = client.get('/api/actas/reporte/', {'folio': folio, 'estado': 'GENERADA'})
    assert len(list(csv.reader(io.StringIO(b''.join(empty_report.streaming_content).decode('utf-8-sig')), delimiter=';'))) == 1
    invalid = client.get('/api/actas/', {'folio': 'ATI-invalido'})
    assert invalid.status_code == 400 and 'folio' in invalid.data
    empty = client.get('/api/actas/', {'folio': 'ATI-2000-000000'})
    assert empty.status_code == 200 and empty.data['count'] == 0
    viewer = User.objects.create_user(username=f'folio_view_{suffix}', password='temporary-only')
    viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
    client.force_authenticate(user=viewer)
    assert client.get('/api/actas/', {'folio': folio}).status_code == 403
    assert client.get('/api/actas/reporte/').status_code == 403
    assert client.get(f'/api/actas/{acta.pk}/integridad/').status_code == 403
    anonymous = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    assert anonymous.get('/api/actas/', {'folio': folio}).status_code in (401, 403)
    assert anonymous.get('/api/actas/reporte/').status_code in (401, 403)
    assert anonymous.get(f'/api/actas/{acta.pk}/integridad/').status_code in (401, 403)
    transaction.set_rollback(True)
assert not ActaEntrega.objects.filter(folio=folio).exists()
print('Archivo ITAM: folio, fechas, CSV, PDF, integridad y permisos OK; rollback confirmado')
