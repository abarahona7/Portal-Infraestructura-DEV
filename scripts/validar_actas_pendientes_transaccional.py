"""Ejecutar con `.venv/bin/python manage.py shell < scripts/validar_actas_pendientes_transaccional.py`."""
import uuid

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from rest_framework.test import APIClient

from core.models import ActaEntrega, Departamento, Equipamiento, Usuario

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    department = Departamento.objects.create(nombre=f'Actas pendientes {suffix}')
    person = Usuario.objects.create(nombre_completo='Persona pendiente', usuario_red=f'pendiente.{suffix}',
        correo_corp=f'pendiente.{suffix}@example.com', departamento=department, rut='11.111.111-1')
    operator = User.objects.create_user(username=f'pendiente_op_{suffix}', password='temporal')
    operator.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=operator)
    actas = []
    for index in range(3):
        asset = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='Pendientes',
            numero_serie=f'PEND-{suffix}-{index}', estado='STOCK', accesorios='Cargador')
        issued = client.post('/api/movimientos/', {
            'tipo_movimiento': 'ASIGNACION', 'activo_id': asset.pk,
            'colaborador_destino_id': person.pk, 'ubicacion_destino': 'Oficina',
            'estado_fisico': 'USADO', 'accesorios_detalle': [{'nombre': 'Cargador', 'entregado': True}],
        }, format='json')
        assert issued.status_code == 201, (issued.status_code, issued.data)
        actas.append(ActaEntrega.objects.get(pk=issued.data['acta']['id']))

    pending = client.post(f'/api/actas/{actas[1].pk}/estado/', {'estado_nuevo': 'PENDIENTE_FIRMA'}, format='json')
    assert pending.status_code == 200, (pending.status_code, pending.data)
    signed_pending = client.post(f'/api/actas/{actas[2].pk}/estado/', {'estado_nuevo': 'PENDIENTE_FIRMA'}, format='json')
    assert signed_pending.status_code == 200, (signed_pending.status_code, signed_pending.data)
    pdf = SimpleUploadedFile('firma.pdf', bytes(actas[2].documento_pdf), content_type='application/pdf')
    signed = client.post(f'/api/actas/{actas[2].pk}/estado/', {'estado_nuevo': 'FIRMADA', 'archivo_firmado': pdf})
    assert signed.status_code == 200, (signed.status_code, signed.data)

    summary = client.get('/api/activos/resumen/')
    assert summary.status_code == 200, (summary.status_code, summary.data)
    assert summary.data['actas_pendientes_firma'] == 2, summary.data
    recent = summary.data['actas_pendientes_recientes']
    assert {row['id'] for row in recent} == {actas[0].pk, actas[1].pk}, recent
    assert {row['estado'] for row in recent} == {'GENERADA', 'PENDIENTE_FIRMA'}, recent
    pages = []
    for page in (1, 2):
        response = client.get('/api/actas/pendientes/', {'page': page, 'page_size': 1})
        assert response.status_code == 200, (response.status_code, response.data)
        assert response['Cache-Control'] == 'no-store, private'
        assert response.data['count'] == 2 and response.data['total_pages'] == 2, response.data
        assert 'documento_pdf' not in response.data['results'][0]
        pages.append(response.data['results'][0]['id'])
    assert set(pages) == {actas[0].pk, actas[1].pk}, pages
    client.force_authenticate(user=None)
    assert client.get('/api/actas/pendientes/').status_code in {401, 403}
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie__startswith=f'PEND-{suffix}').exists()
print('Actas pendientes: estados vigentes, paginación, permisos y rollback OK')
