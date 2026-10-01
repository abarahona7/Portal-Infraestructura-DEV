"""Ejecutar con `python manage.py shell < scripts/validar_dashboard_itam.py`."""
import uuid
from unittest.mock import patch
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
    with patch.object(Equipamiento.objects, 'all', return_value=Equipamiento.objects.filter(pk=asset.pk)):
        named = client.get('/api/activos/resumen/')
        assert named.status_code == 200, (named.status_code, named.data)
        assert named.data['por_area'] == [{'nombre': department.nombre, 'total': 1}]
        department.nombre = f'Tecnología {suffix}'
        department.save()
        renamed = client.get('/api/activos/resumen/')
        assert renamed.status_code == 200, (renamed.status_code, renamed.data)
        assert renamed.data['por_area'] == [{'nombre': department.nombre, 'total': 1}]
        assert person.dpto_area != department.nombre
    assert assigned.data['ultimos_movimientos'][0]['folio'] == movement.data['acta']['folio']
    assert 'rut' not in str(assigned.data).lower()
    licencia = Usuario.objects.create(nombre_completo='Persona en licencia', usuario_red=f'lic.{suffix}',
        correo_corp=f'lic.{suffix}@example.com', departamento=department, estado='LICENCIA')
    en_revision = [Equipamiento.objects.create(tipo='Monitor', marca='Prueba', modelo='Custodia',
        numero_serie=f'LIC-{suffix}-{index}', estado='ASIGNADO', usuario=licencia)
        for index in range(2)]
    custody_summary = client.get('/api/activos/resumen/')
    assert custody_summary.status_code == 200, (custody_summary.status_code, custody_summary.data)
    assert custody_summary.data['conteos']['con_custodio_inactivo'] == original['con_custodio_inactivo'] + 2
    assert [row['id'] for row in custody_summary.data['custodios_no_activos_recientes'][:2]] == [
        en_revision[1].pk, en_revision[0].pk,
    ]
    assert custody_summary.data['custodios_no_activos_recientes'][0]['colaborador']['estado'] == 'LICENCIA'
    custody_page = client.get('/api/activos/custodios-no-activos/?page=1&page_size=1')
    assert custody_page.status_code == 200, (custody_page.status_code, custody_page.data)
    assert custody_page.data['count'] == custody_summary.data['conteos']['con_custodio_inactivo']
    assert custody_page.data['results'][0]['id'] == en_revision[1].pk
    assert custody_page['Cache-Control'] == 'no-store, private'
    assert 'rut' not in str(custody_page.data).lower() and 'correo_corp' not in str(custody_page.data).lower()
    custody_next = client.get('/api/activos/custodios-no-activos/?page=2&page_size=1')
    assert custody_next.status_code == 200 and custody_next.data['results'][0]['id'] == en_revision[0].pk
    mantenimiento = Equipamiento.objects.create(tipo='Monitor', marca='Prueba', modelo='Taller',
        numero_serie=f'MAN-{suffix}', estado='MANTENCION', ubicacion_actual='Taller TI')
    unassigned_summary = client.get('/api/activos/resumen/')
    assert unassigned_summary.data['conteos']['sin_custodio'] == original['sin_custodio'] + 3
    unassigned = client.get('/api/activos/sin-custodio/?page=1&page_size=2')
    assert unassigned.status_code == 200, (unassigned.status_code, unassigned.data)
    assert unassigned.data['count'] == unassigned_summary.data['conteos']['sin_custodio']
    assert [row['id'] for row in unassigned.data['results']] == [mantenimiento.pk, baja.pk]
    assert unassigned['Cache-Control'] == 'no-store, private'
    unassigned_next = client.get('/api/activos/sin-custodio/?page=2&page_size=2')
    assert unassigned_next.status_code == 200 and unassigned_next.data['results'][0]['id'] == celular.pk
    in_repair = client.get('/api/activos/sin-custodio/', {'estado': 'MANTENCION', 'page_size': 1})
    assert in_repair.status_code == 200 and in_repair.data['results'][0]['id'] == mantenimiento.pk
    assert asset.pk not in [row['id'] for row in unassigned.data['results']]
    assert 'rut' not in str(unassigned.data).lower() and 'correo' not in str(unassigned.data).lower()
    invalid_state = client.get('/api/activos/sin-custodio/', {'estado': 'INVENTADO'})
    assert invalid_state.status_code == 400 and 'estado' in invalid_state.data
    anonymous = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    assert anonymous.get('/api/activos/resumen/').status_code in (401, 403)
    assert anonymous.get('/api/activos/pendientes-tecnicos/').status_code in (401, 403)
    assert anonymous.get('/api/activos/custodios-no-activos/').status_code in (401, 403)
    assert anonymous.get('/api/activos/sin-custodio/').status_code in (401, 403)
    viewer = User.objects.create_user(username=f'dashboard_view_{suffix}', password='temporary-only')
    viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
    client.force_authenticate(user=viewer)
    assert client.get('/api/activos/resumen/').status_code == 403
    assert client.get('/api/activos/pendientes-tecnicos/').status_code == 403
    assert client.get('/api/activos/custodios-no-activos/').status_code == 403
    assert client.get('/api/activos/sin-custodio/').status_code == 403
    transaction.set_rollback(True)
assert not Usuario.objects.filter(usuario_red=f'dash.{suffix}').exists()
print('Dashboard ITAM: conteos, activos sin custodio, distribución y permisos OK; rollback confirmado')
