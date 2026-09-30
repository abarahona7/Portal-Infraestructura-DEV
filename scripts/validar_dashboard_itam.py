"""Ejecutar con `python manage.py shell < scripts/validar_dashboard_itam.py`."""
import uuid
from django.contrib.auth.models import Group, User
from django.db import transaction
from rest_framework.test import APIClient
from core.models import Departamento, Equipamiento, Usuario

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    actor = User.objects.create_user(username=f'dashboard_op_{suffix}', password='temporary-only')
    actor.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=actor)
    baseline = client.get('/api/activos/resumen/')
    assert baseline.status_code == 200, (baseline.status_code, baseline.data)
    original = baseline.data['conteos']
    department = Departamento.objects.create(nombre=f'Dashboard TI {suffix}')
    person = Usuario.objects.create(nombre_completo='Persona tablero', usuario_red=f'dash.{suffix}',
        correo_corp=f'dash.{suffix}@example.com', departamento=department, rut='11.111.111-1')
    asset = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='Dashboard',
        numero_serie=None, af=None, estado='STOCK', ubicacion_actual='Bodega tablero')
    available = client.get('/api/activos/resumen/')
    assert available.status_code == 200, (available.status_code, available.data)
    assert available.data['conteos']['total'] == original['total'] + 1
    assert available.data['conteos']['disponibles'] == original['disponibles'] + 1
    assert available.data['conteos']['sin_serie'] == original['sin_serie'] + 1
    assert available.data['conteos']['sin_activo_fijo'] == original['sin_activo_fijo'] + 1
    assert available.data['conteos']['sin_hostname_computador'] == original['sin_hostname_computador'] + 1
    assert available.data['conteos']['sin_mac_computador'] == original['sin_mac_computador'] + 1
    assert available.data['conteos']['fichas_tecnicas_incompletas'] == original['fichas_tecnicas_incompletas'] + 1
    assert available.data['pendientes_tecnicos'][0]['id'] == asset.pk
    assert available.data['pendientes_tecnicos'][0]['faltantes'] == ['Hostname', 'MAC Address']
    celular = Equipamiento.objects.create(tipo='Celular', marca='Prueba', modelo='Sin IMEI',
        numero_serie=f'DASH-CEL-{suffix}', estado='STOCK')
    baja = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='Baja',
        numero_serie=f'DASH-BAJA-{suffix}', estado='BAJA')
    quality = client.get('/api/activos/resumen/')
    assert quality.status_code == 200, (quality.status_code, quality.data)
    assert quality.data['conteos']['sin_imei_celular'] == original['sin_imei_celular'] + 1
    assert quality.data['conteos']['fichas_tecnicas_incompletas'] == original['fichas_tecnicas_incompletas'] + 2
    assert quality.data['pendientes_tecnicos'][0]['id'] == celular.pk
    assert not any(item['id'] == baja.pk for item in quality.data['pendientes_tecnicos'])
    paged = client.get('/api/activos/pendientes-tecnicos/?page=1&page_size=2')
    assert paged.status_code == 200, (paged.status_code, paged.data)
    assert paged.data['count'] == quality.data['conteos']['fichas_tecnicas_incompletas']
    assert paged.data['page_size'] == 2 and len(paged.data['results']) == 2
    assert [item['id'] for item in paged.data['results']] == [celular.pk, asset.pk]
    assert paged['Cache-Control'] == 'no-store, private'
    next_page = client.get('/api/activos/pendientes-tecnicos/?page=2&page_size=2')
    assert next_page.status_code == 200 and next_page.data['page'] == 2
    assert next_page.data['results'][0]['id'] != celular.pk
    assert any(row['nombre'] == 'Bodega tablero' for row in available.data['por_ubicacion'])
    movement = client.post('/api/movimientos/', {'tipo_movimiento': 'ASIGNACION', 'activo_id': asset.pk,
        'colaborador_destino_id': person.pk, 'ubicacion_destino': 'Oficina tablero',
        'estado_fisico': 'USADO', 'accesorios_detalle': []}, format='json')
    assert movement.status_code == 201, (movement.status_code, movement.data)
    assigned = client.get('/api/activos/resumen/')
    assert assigned.status_code == 200, (assigned.status_code, assigned.data)
    assert assigned.data['conteos']['disponibles'] == original['disponibles'] + 1
    assert assigned.data['conteos']['asignados'] == original['asignados'] + 1
    assert assigned.data['conteos']['fichas_tecnicas_incompletas'] == original['fichas_tecnicas_incompletas'] + 2
    assert assigned.data['movimientos_30_dias'] == baseline.data['movimientos_30_dias'] + 1
    assert sum(row['total'] for row in assigned.data['por_area']) == sum(row['total'] for row in baseline.data['por_area']) + 1
    assert assigned.data['ultimos_movimientos'][0]['folio'] == movement.data['acta']['folio']
    assert 'rut' not in str(assigned.data).lower()
    anonymous = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    assert anonymous.get('/api/activos/resumen/').status_code in (401, 403)
    assert anonymous.get('/api/activos/pendientes-tecnicos/').status_code in (401, 403)
    viewer = User.objects.create_user(username=f'dashboard_view_{suffix}', password='temporary-only')
    viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
    client.force_authenticate(user=viewer)
    assert client.get('/api/activos/resumen/').status_code == 403
    assert client.get('/api/activos/pendientes-tecnicos/').status_code == 403
    transaction.set_rollback(True)
assert not Usuario.objects.filter(usuario_red=f'dash.{suffix}').exists()
print('Dashboard ITAM: conteos, distribución, movimientos y permisos OK; rollback confirmado')
