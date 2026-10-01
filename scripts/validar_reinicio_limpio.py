"""Prueba reversible de la gestión original, tablero, QR y acta tradicional."""
import uuid

from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.test import APIClient

from core.models import Departamento, Equipamiento, Usuario

suffix = uuid.uuid4().hex[:8]
with transaction.atomic():
    admin = User.objects.create_superuser(username=f'clean_{suffix}', password='temporary-only')
    depto = Departamento.objects.create(nombre=f'Tecnología Prueba {suffix}')
    person = Usuario.objects.create(nombre_completo='Persona de prueba', usuario_red=f'clean.{suffix}',
                                    correo_corp=f'clean.{suffix}@example.com', departamento=depto)
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=admin)
    created = client.post('/api/equipos/', {'tipo': 'Notebook', 'marca': 'Prueba', 'modelo': 'Limpio',
                                           'numero_serie': f'CLEAN-{suffix}', 'estado': 'STOCK'}, format='json')
    assert created.status_code == 201, (created.status_code, created.data)
    asset_id = created.data['id']
    asset = Equipamiento.objects.get(pk=asset_id)
    assert asset.token_qr
    assigned = client.patch(f'/api/equipos/{asset_id}/', {'usuario': person.pk, 'estado': 'ASIGNADO'}, format='json')
    assert assigned.status_code == 200, (assigned.status_code, assigned.data)
    summary = client.get('/api/activos/resumen/')
    assert summary.status_code == 200
    assert any(row['id'] == depto.pk for row in summary.data['departamentos'])
    department_assets = client.get('/api/equipos/', {'departamento_id': depto.pk})
    assert department_assets.status_code == 200 and department_assets.data['count'] == 1
    qr_path = f'/api/activos/qr/{asset.token_qr}/'
    qr = client.get(qr_path)
    assert qr.status_code == 200 and qr.data['equipo']['departamento'] == depto.nombre
    assert 'rut' not in qr.data['equipo'] and 'ubicacion' not in qr.data['equipo']
    qr_image = client.get(f'{qr_path}imagen/')
    assert qr_image.status_code == 200 and qr_image.content.startswith(b'<?xml')
    acta = client.get(f'/api/usuarios/{person.pk}/acta-entrega/')
    assert acta.status_code == 200 and acta.content.startswith(b'%PDF-')
    anonymous = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    assert anonymous.get(qr_path).status_code in (401, 403)
    returned = client.patch(f'/api/equipos/{asset_id}/', {'usuario': None, 'estado': 'STOCK'}, format='json')
    assert returned.status_code == 200, (returned.status_code, returned.data)
    qr_unassigned = client.get(qr_path)
    assert qr_unassigned.data['equipo']['departamento'] is None
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie=f'CLEAN-{suffix}').exists()
print('Gestión original, acta, tablero y QR: OK (rollback confirmado)')
