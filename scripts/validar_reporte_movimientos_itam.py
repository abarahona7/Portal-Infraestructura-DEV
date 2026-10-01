"""Ejecutar con `python manage.py shell < scripts/validar_reporte_movimientos_itam.py`."""
import csv
import io
import uuid
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Equipamiento, MovimientoActivo

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    operator = User.objects.create_user(username=f'report_op_{suffix}', password='temporary-only')
    operator.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    asset = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='Reporte',
        numero_serie=f'REPORT-{suffix}', estado='STOCK', ubicacion_actual='Bodega')
    today = timezone.now()
    recent = MovimientoActivo.objects.create(activo=asset, tipo_movimiento='ALTA',
        fecha_movimiento=today, ubicacion_destino='=SUM(1,1)',
        estado_operativo_resultante='STOCK', ejecutado_por='=cmd')
    old = MovimientoActivo.objects.create(activo=asset, tipo_movimiento='BAJA',
        fecha_movimiento=today - timedelta(days=10), ubicacion_destino='Bodega',
        estado_operativo_resultante='BAJA', ejecutado_por='Operador')
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=operator)
    response = client.get('/api/movimientos/reporte/')
    assert response.status_code == 200, response.status_code
    assert response['Content-Type'].startswith('text/csv')
    assert response['Cache-Control'] == 'no-store, private'
    assert response['X-Content-Type-Options'] == 'nosniff'
    body = b''.join(response.streaming_content).decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(body), delimiter=';'))
    assert rows[0][0] == 'ID movimiento'
    assert [row[0] for row in rows].index(str(recent.pk)) < [row[0] for row in rows].index(str(old.pk))
    recent_row = next(row for row in rows if row[0] == str(recent.pk))
    assert 'Ubicación' not in ';'.join(rows[0]) and recent_row[-1] == "'=cmd"
    assert 'snapshot' not in body.lower() and 'documento_pdf' not in body.lower()
    current_date = timezone.localdate(today).isoformat()
    filtered = client.get('/api/movimientos/reporte/', {
        'desde': current_date, 'hasta': current_date, 'tipo_movimiento': 'ALTA',
    })
    assert filtered.status_code == 200
    filtered_rows = list(csv.reader(io.StringIO(b''.join(filtered.streaming_content).decode('utf-8-sig')), delimiter=';'))
    assert str(recent.pk) in [row[0] for row in filtered_rows[1:]]
    assert str(old.pk) not in [row[0] for row in filtered_rows[1:]]
    assert all(row[2] == 'ALTA' for row in filtered_rows[1:])
    assert client.get('/api/movimientos/reporte/', {'desde': 'ayer'}).status_code == 400
    assert client.get('/api/movimientos/reporte/', {'tipo_movimiento': 'INVENTADO'}).status_code == 400
    assert client.get('/api/movimientos/reporte/', {
        'desde': current_date, 'hasta': (timezone.localdate(today) - timedelta(days=1)).isoformat(),
    }).status_code == 400
    viewer = User.objects.create_user(username=f'report_view_{suffix}', password='temporary-only')
    viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
    client.force_authenticate(user=viewer)
    assert client.get('/api/movimientos/reporte/').status_code == 403
    anonymous = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    assert anonymous.get('/api/movimientos/reporte/').status_code in (401, 403)
    transaction.set_rollback(True)
assert not User.objects.filter(username=f'report_op_{suffix}').exists()
print('Reporte ITAM: CSV, filtros, roles y protección de fórmulas OK; rollback confirmado')
