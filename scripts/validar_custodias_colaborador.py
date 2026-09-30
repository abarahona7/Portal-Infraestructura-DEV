"""Ejecutar con `.venv/bin/python manage.py shell < scripts/validar_custodias_colaborador.py`."""
import uuid
from datetime import date

from django.contrib.auth.models import Group, User
from django.db import transaction
from rest_framework.test import APIClient

from core.models import Departamento, Equipamiento, Usuario

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    department = Departamento.objects.create(nombre=f'Validación custodias {suffix}')
    first = Usuario.objects.create(nombre_completo='Primera Persona', usuario_red=f'cust1.{suffix}',
        correo_corp=f'cust1.{suffix}@example.com', departamento=department, rut='11.111.111-1')
    second = Usuario.objects.create(nombre_completo='Segunda Persona', usuario_red=f'cust2.{suffix}',
        correo_corp=f'cust2.{suffix}@example.com', departamento=department, rut='12.345.678-5')
    operator = User.objects.create_user(username=f'cust_op_{suffix}', password='temporary-only')
    operator.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=operator)
    asset = Equipamiento.objects.create(tipo='Notebook', marca='Validación', modelo='A',
        numero_serie=f'CUST-A-{suffix}', estado='STOCK')
    legacy_out = Equipamiento.objects.create(tipo='Notebook', marca='Validación', modelo='B',
        numero_serie=f'CUST-B-{suffix}', estado='ASIGNADO', usuario=first,
        fecha_asignacion=date(2026, 1, 2))
    legacy_current = Equipamiento.objects.create(tipo='Notebook', marca='Validación', modelo='C',
        numero_serie=f'CUST-C-{suffix}', estado='ASIGNADO', usuario=first,
        fecha_asignacion=date(2026, 2, 3))
    def move(kind, equipment, *, origin=None, destination=None):
        payload = {'tipo_movimiento': kind, 'activo_id': equipment.pk,
                   'ubicacion_destino': 'Bodega TI' if kind == 'DEVOLUCION' else 'Oficina',
                   'estado_fisico': 'USADO', 'accesorios_detalle': []}
        if origin: payload['colaborador_origen_id'] = origin.pk
        if destination: payload['colaborador_destino_id'] = destination.pk
        response = client.post('/api/movimientos/', payload, format='json')
        assert response.status_code == 201, (response.status_code, response.data)
        return response.data
    delivered = move('ASIGNACION', asset, destination=first)
    transferred = move('REASIGNACION', asset, origin=first, destination=second)
    returned = move('DEVOLUCION', legacy_out, origin=first)
    given_back = move('REASIGNACION', asset, origin=second, destination=first)
    result = client.get(f'/api/movimientos/custodias/?colaborador_id={first.pk}')
    assert result.status_code == 200, (result.status_code, result.data)
    periods = result.data
    assert len(periods) == 4, periods
    first_asset = [item for item in periods if item['activo']['id'] == asset.pk]
    assert len(first_asset) == 2
    assert any(item['estado'] == 'FINALIZADO' and item['folio_entrega'] == delivered['acta']['folio']
               and item['folio_salida'] == transferred['acta']['folio'] for item in first_asset)
    assert any(item['estado'] == 'VIGENTE' and item['folio_entrega'] == given_back['acta']['folio'] for item in first_asset)
    legacy_period = next(item for item in periods if item['activo']['id'] == legacy_out.pk)
    assert legacy_period['estado'] == 'FINALIZADO' and legacy_period['fecha_asignacion'] == '2026-01-02'
    assert legacy_period['folio_entrega'] is None and legacy_period['folio_salida'] == returned['acta']['folio']
    current_period = next(item for item in periods if item['activo']['id'] == legacy_current.pk)
    assert current_period['estado'] == 'VIGENTE' and current_period['fecha_asignacion'] == '2026-02-03'
    assert current_period['folio_entrega'] is None
    second_periods = client.get(f'/api/movimientos/custodias/?colaborador_id={second.pk}').data
    assert len(second_periods) == 1 and second_periods[0]['estado'] == 'FINALIZADO'
    assert second_periods[0]['folio_entrega'] == transferred['acta']['folio']
    assert second_periods[0]['folio_salida'] == given_back['acta']['folio']
    assert client.get('/api/movimientos/custodias/').status_code == 400
    assert client.get('/api/movimientos/custodias/?colaborador_id=999999999').status_code == 404
    viewer = User.objects.create_user(username=f'cust_view_{suffix}', password='temporary-only')
    viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
    client.force_authenticate(user=viewer)
    assert client.get(f'/api/movimientos/custodias/?colaborador_id={first.pk}').status_code == 403
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie=f'CUST-A-{suffix}').exists()
print('Custodias: períodos ITAM/legados, folios, estado y permisos OK; rollback completo')
