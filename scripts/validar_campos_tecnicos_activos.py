"""Ejecutar con `.venv/bin/python manage.py shell < scripts/validar_campos_tecnicos_activos.py`."""
import uuid
from django.contrib.auth.models import Group, User
from django.db import transaction
from rest_framework.test import APIClient
from core.models import Equipamiento

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    actor = User.objects.create_user(username=f'campos_{suffix}', password='temporary-only')
    actor.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=actor)
    base = {'marca': 'Validación', 'modelo': 'Técnico', 'estado': 'STOCK'}
    def create(tipo, serial, **fields):
        return client.post('/api/equipos/', {**base, 'tipo': tipo,
            'numero_serie': f'{serial}-{suffix}', **fields}, format='json')
    assert create('Celular', 'CEL-NO').status_code == 400
    celular = create('Celular', 'CEL-OK', imei='123456789012345')
    assert celular.status_code == 201, (celular.status_code, celular.data)
    assert create('Notebook', 'NB-NO').status_code == 400
    assert create('Notebook', 'NB-HOST', hostname=f'NB-{suffix}').status_code == 400
    notebook = create('Notebook', 'NB-OK', hostname=f'NB2-{suffix}', mac_address='AA:BB:CC:DD:EE:FF')
    assert notebook.status_code == 201, (notebook.status_code, notebook.data)
    assert client.patch(f"/api/equipos/{notebook.data['id']}/", {'mac_address': ''}, format='json').status_code == 400
    assert client.patch(f"/api/equipos/{notebook.data['id']}/", {'hostname': ''}, format='json').status_code == 400
    assert client.patch(f"/api/equipos/{celular.data['id']}/", {'imei': ''}, format='json').status_code == 400
    monitor = create('Monitor', 'MON-OK')
    assert monitor.status_code == 201, (monitor.status_code, monitor.data)

    legacy = Equipamiento.objects.create(tipo='Notebook', marca='Legado', modelo='Sin MAC',
        numero_serie=f'LEG-{suffix}', estado='STOCK')
    edited = client.patch(f'/api/equipos/{legacy.pk}/', {'marca': 'Legado revisado'}, format='json')
    assert edited.status_code == 200, (edited.status_code, edited.data)
    switched_invalid = client.patch(f'/api/equipos/{legacy.pk}/', {'tipo': 'Celular'}, format='json')
    assert switched_invalid.status_code == 400 and 'imei' in switched_invalid.data
    switched = client.patch(f'/api/equipos/{legacy.pk}/', {'tipo': 'Celular', 'imei': '987654321098765'}, format='json')
    assert switched.status_code == 200, (switched.status_code, switched.data)
    assert switched.data['tipo'] == 'Celular' and switched.data['imei'] == '987654321098765'
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie=f'LEG-{suffix}').exists()
print('Campos técnicos: altas, cambio de tipo y edición legada OK; rollback completo')
