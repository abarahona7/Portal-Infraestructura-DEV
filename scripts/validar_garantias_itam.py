"""Ejecutar con `python manage.py shell < scripts/validar_garantias_itam.py`."""
import uuid
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Equipamiento, HistorialEquipo
from core.serializers import EquipamientoSerializer

suffix = uuid.uuid4().hex[:10]
today = timezone.localdate()
with transaction.atomic():
    operator = User.objects.create_user(username=f'warranty_op_{suffix}', password='temporary-only')
    operator.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=operator)
    baseline = client.get('/api/activos/resumen/')
    assert baseline.status_code == 200
    before = baseline.data['conteos']
    assert baseline.data['ventana_garantia_dias'] == 30

    def asset(label, due, state='STOCK'):
        return Equipamiento.objects.create(tipo='Monitor', marca='Prueba', modelo=label,
            numero_serie=f'G{suffix[:7]}{label[:8]}', estado=state,
            fecha_vencimiento_garantia=due)

    due_today = asset('Today', today)
    near = asset('Near', today + timedelta(days=5))
    boundary = asset('Boundary', today + timedelta(days=30))
    expired = asset('Expired', today - timedelta(days=1))
    future = asset('Future', today + timedelta(days=31))
    retired = asset('Retired', today - timedelta(days=1), 'BAJA')
    undated = asset('Undated', None)
    summary = client.get('/api/activos/resumen/')
    assert summary.status_code == 200, (summary.status_code, summary.data)
    counts = summary.data['conteos']
    assert counts['garantias_proximas'] == before['garantias_proximas'] + 3
    assert counts['garantias_vencidas'] == before['garantias_vencidas'] + 1
    assert counts['garantias_sin_fecha'] == before['garantias_sin_fecha'] + 1
    assert summary.data['garantias_sin_fecha_recientes'][0]['id'] == undated.pk
    assert summary.data['garantias_sin_fecha_recientes'][0]['dias_para_vencer'] is None
    assert {due_today.pk, near.pk, boundary.pk}.issubset({row['id'] for row in summary.data['garantias_proximas_recientes']})
    assert next(row for row in summary.data['garantias_proximas_recientes'] if row['id'] == due_today.pk)['dias_para_vencer'] == 0
    assert expired.pk in {row['id'] for row in summary.data['garantias_vencidas_recientes']}
    assert all(row['id'] not in {future.pk, retired.pk, undated.pk}
        for row in summary.data['garantias_proximas_recientes'] + summary.data['garantias_vencidas_recientes'])
    upcoming = client.get('/api/activos/garantias/?estado=proximas&page_size=1')
    assert upcoming.status_code == 200 and upcoming.data['count'] == counts['garantias_proximas']
    assert upcoming['Cache-Control'] == 'no-store, private'
    assert upcoming.data['results'][0]['dias_para_vencer'] >= 0
    expired_list = client.get('/api/activos/garantias/?estado=vencidas&page_size=20')
    assert expired_list.status_code == 200 and expired_list.data['count'] == counts['garantias_vencidas']
    assert any(row['id'] == expired.pk and row['dias_para_vencer'] == -1 for row in expired_list.data['results'])
    missing = client.get('/api/activos/garantias/?estado=sin_fecha&page_size=1')
    assert missing.status_code == 200 and missing.data['count'] == counts['garantias_sin_fecha']
    assert missing.data['results'][0]['id'] == undated.pk
    assert missing.data['results'][0]['fecha_vencimiento_garantia'] is None
    assert missing.data['results'][0]['dias_para_vencer'] is None
    assert client.get('/api/activos/garantias/?estado=otro').status_code == 400
    assert 'rut' not in str(expired_list.data).lower() and 'correo' not in str(expired_list.data).lower()

    form = EquipamientoSerializer(data={'tipo': 'Monitor', 'marca': 'Prueba', 'modelo': 'Nuevo',
        'fecha_vencimiento_garantia': today.isoformat()})
    assert form.is_valid(), form.errors
    assert form.validated_data['fecha_vencimiento_garantia'] == today
    invalid = EquipamientoSerializer(data={'tipo': 'Monitor', 'marca': 'Prueba', 'modelo': 'Nuevo',
        'fecha_vencimiento_garantia': 'fecha inválida'})
    assert not invalid.is_valid() and 'fecha_vencimiento_garantia' in invalid.errors
    cleared = client.patch(f'/api/equipos/{future.pk}/', {'fecha_vencimiento_garantia': None}, format='json')
    assert cleared.status_code == 200, (cleared.status_code, cleared.data)
    future.refresh_from_db()
    assert future.fecha_vencimiento_garantia is None
    refreshed_missing = client.get('/api/activos/garantias/?estado=sin_fecha&page_size=20')
    assert refreshed_missing.data['count'] == before['garantias_sin_fecha'] + 2
    assert future.pk in {row['id'] for row in refreshed_missing.data['results']}
    history = HistorialEquipo.objects.filter(equipo=future).order_by('-pk').first()
    assert history and 'Vencimiento Garantía' in history.observacion
    assert history.modificado_por == operator.username

    viewer = User.objects.create_user(username=f'warranty_view_{suffix}', password='temporary-only')
    viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
    client.force_authenticate(user=viewer)
    assert client.get('/api/activos/garantias/').status_code == 403
    anonymous = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    assert anonymous.get('/api/activos/garantias/').status_code in (401, 403)
    transaction.set_rollback(True)
assert not User.objects.filter(username=f'warranty_op_{suffix}').exists()
print('Garantías ITAM: fecha opcional, ventana, baja, listas, edición y permisos OK; rollback confirmado')
