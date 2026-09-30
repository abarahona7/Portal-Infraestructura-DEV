"""Ejecutar con `python manage.py shell < scripts/validar_identificadores_faltantes_itam.py`."""
import uuid

from django.contrib.auth.models import Group, User
from django.db import transaction
from rest_framework.test import APIClient

from core.models import Equipamiento

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    operator = User.objects.create_user(username=f'ident_op_{suffix}', password='temporary-only')
    operator.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=operator)
    baseline = client.get('/api/activos/resumen/')
    assert baseline.status_code == 200, (baseline.status_code, baseline.data)
    counts = baseline.data['conteos']

    both = Equipamiento.objects.create(tipo='Monitor', marca='Prueba', modelo='Ambos',
        numero_serie=None, af=None, estado='STOCK', ubicacion_actual='Bodega prueba')
    only_serial = Equipamiento.objects.create(tipo='Monitor', marca='Prueba', modelo='Serie',
        numero_serie=f'SN{suffix}', af=None, estado='STOCK')
    only_af = Equipamiento.objects.create(tipo='Monitor', marca='Prueba', modelo='AF',
        numero_serie=None, af=f'AF{suffix}', estado='BAJA')
    complete = Equipamiento.objects.create(tipo='Monitor', marca='Prueba', modelo='Completo',
        numero_serie=f'OK{suffix}', af=f'OK{suffix}', estado='STOCK')

    summary = client.get('/api/activos/resumen/')
    assert summary.status_code == 200
    assert summary.data['conteos']['sin_serie'] == counts['sin_serie'] + 2
    assert summary.data['conteos']['sin_activo_fijo'] == counts['sin_activo_fijo'] + 2

    serials = client.get('/api/activos/identificadores-faltantes/', {'campo': 'serie', 'page_size': 1})
    assert serials.status_code == 200, (serials.status_code, serials.data)
    assert serials.data['count'] == summary.data['conteos']['sin_serie']
    assert serials.data['results'][0]['id'] == only_af.pk
    assert serials.data['results'][0]['estado'] == 'BAJA'
    assert serials['Cache-Control'] == 'no-store, private'
    second = client.get('/api/activos/identificadores-faltantes/', {'campo': 'serie', 'page_size': 1, 'page': 2})
    assert second.status_code == 200 and second.data['results'][0]['id'] == both.pk

    assets = client.get('/api/activos/identificadores-faltantes/', {'campo': 'activo_fijo', 'page_size': 2})
    assert assets.status_code == 200, (assets.status_code, assets.data)
    assert assets.data['count'] == summary.data['conteos']['sin_activo_fijo']
    assert [item['id'] for item in assets.data['results']] == [only_serial.pk, both.pk]
    assert complete.pk not in [item['id'] for item in assets.data['results']]
    assert 'rut' not in str(assets.data).lower() and 'correo' not in str(assets.data).lower()
    Equipamiento.objects.filter(pk=complete.pk).update(numero_serie='', af='')
    blank_summary = client.get('/api/activos/resumen/')
    assert blank_summary.data['conteos']['sin_serie'] == counts['sin_serie'] + 3
    assert blank_summary.data['conteos']['sin_activo_fijo'] == counts['sin_activo_fijo'] + 3
    blank_serial = client.get('/api/activos/identificadores-faltantes/', {'campo': 'serie', 'page_size': 1})
    blank_af = client.get('/api/activos/identificadores-faltantes/', {'campo': 'activo_fijo', 'page_size': 1})
    assert blank_serial.data['results'][0]['id'] == complete.pk
    assert blank_af.data['results'][0]['id'] == complete.pk
    invalid = client.get('/api/activos/identificadores-faltantes/', {'campo': 'imei'})
    assert invalid.status_code == 400 and 'campo' in invalid.data

    anonymous = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    assert anonymous.get('/api/activos/identificadores-faltantes/', {'campo': 'serie'}).status_code in (401, 403)
    viewer = User.objects.create_user(username=f'ident_view_{suffix}', password='temporary-only')
    viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
    client.force_authenticate(user=viewer)
    assert client.get('/api/activos/identificadores-faltantes/', {'campo': 'serie'}).status_code == 403
    transaction.set_rollback(True)

assert not Equipamiento.objects.filter(pk=both.pk).exists()
print('Identificadores ITAM: conteos, filtros, paginación y permisos OK; rollback confirmado')
