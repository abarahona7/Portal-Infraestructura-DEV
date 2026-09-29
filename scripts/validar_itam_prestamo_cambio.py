"""Ejecutar con `python manage.py shell < scripts/validar_itam_prestamo_cambio.py`."""
import hashlib
import uuid
from io import BytesIO
from unittest.mock import patch
from django.contrib.auth.models import Group, User
from django.db import transaction
from rest_framework.test import APIClient
from core.models import Departamento, Equipamiento, MovimientoActivo, SecurityAuditLog, Usuario
from core.services.acta_entrega_pdf import generar_acta_custodia_pdf

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    department = Departamento.objects.create(nombre=f'Prueba cambio {suffix}')
    person = Usuario.objects.create(nombre_completo='Persona cambio', usuario_red=f'cambio.{suffix}',
        correo_corp=f'cambio.{suffix}@example.com', departamento=department, rut='11.111.111-1')
    actor = User.objects.create_user(username=f'cambio_op_{suffix}', password='temporary-only')
    actor.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    client = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    client.force_authenticate(user=actor)
    old = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='Antiguo',
        numero_serie=f'C-OLD-{suffix}', estado='STOCK', accesorios='Cargador')
    new = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='Nuevo',
        numero_serie=f'C-NEW-{suffix}', estado='STOCK', accesorios='Cable')
    loan = client.post('/api/movimientos/', {'tipo_movimiento': 'PRESTAMO', 'activo_id': old.pk,
        'colaborador_destino_id': person.pk, 'ubicacion_destino': 'Oficina',
        'estado_fisico': 'USADO', 'accesorios_detalle': [{'nombre': 'Cargador', 'entregado': True}]}, format='json')
    assert loan.status_code == 201, (loan.status_code, loan.data)
    old.refresh_from_db()
    assert old.estado == 'PRESTAMO' and old.usuario_id == person.pk
    assert client.post('/api/movimientos/', {'tipo_movimiento': 'PRESTAMO', 'activo_id': old.pk,
        'colaborador_destino_id': person.pk, 'ubicacion_destino': 'Oficina',
        'estado_fisico': 'USADO', 'accesorios_detalle': []}, format='json').status_code == 409

    def exchange(old_asset, replacement):
        return client.post('/api/movimientos/cambio/', {
            'activo_origen_id': old_asset.pk, 'activo_destino_id': replacement.pk,
            'colaborador_id': person.pk, 'ubicacion_retorno': 'Bodega TI',
            'ubicacion_entrega': 'Oficina', 'estado_fisico_origen': 'USADO',
            'estado_fisico_destino': 'NUEVO', 'estado_operativo_origen': 'STOCK',
            'accesorios_devueltos': [{'nombre': 'Cargador', 'entregado': True}],
            'accesorios_entregados': [{'nombre': 'Cable', 'entregado': True}],
            'observaciones': 'Cambio por renovación',
        }, format='json')
    changed = exchange(old, new)
    assert changed.status_code == 201, (changed.status_code, changed.data)
    assert changed.data['tipo_operacion'] == 'CAMBIO'
    assert changed.data['salida']['tipo_movimiento'] == 'DEVOLUCION'
    assert changed.data['entrada']['tipo_movimiento'] == 'CAMBIO'
    assert changed.data['salida']['operacion_id'] == changed.data['entrada']['operacion_id'] == changed.data['operacion_id']
    assert int(changed.data['entrada']['acta']['folio'][-6:]) == int(changed.data['salida']['acta']['folio'][-6:]) + 1
    old.refresh_from_db(); new.refresh_from_db()
    assert old.estado == 'STOCK' and old.usuario_id is None
    assert new.estado == 'ASIGNADO' and new.usuario_id == person.pk
    assert MovimientoActivo.objects.filter(operacion_id=changed.data['operacion_id']).count() == 2
    paired = client.get(f"/api/movimientos/?operacion_id={changed.data['operacion_id']}")
    assert paired.status_code == 200 and paired.data['count'] == 2
    assert client.get('/api/movimientos/?operacion_id=invalido').status_code == 400
    for phase in ('salida', 'entrada'):
        acta = changed.data[phase]['acta']
        pdf = client.get(f"/api/actas/{acta['id']}/pdf/")
        assert pdf.status_code == 200 and hashlib.sha256(pdf.content).hexdigest() == acta['hash_verificacion']
    assert exchange(old, new).status_code == 409

    last_folio = int(changed.data['entrada']['acta']['folio'][-6:])
    third = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='Tercero',
        numero_serie=f'C-THIRD-{suffix}', estado='STOCK', accesorios='Adaptador')
    count_before = MovimientoActivo.objects.count()
    call_count = 0
    def fail_second(snapshot):
        global call_count
        call_count += 1
        return generar_acta_custodia_pdf(snapshot) if call_count == 1 else BytesIO(b'INVALIDO')
    with patch('core.services.asset_lifecycle_service.generar_acta_custodia_pdf', side_effect=fail_second):
        failed = client.post('/api/movimientos/cambio/', {
            'activo_origen_id': new.pk, 'activo_destino_id': third.pk,
            'colaborador_id': person.pk, 'ubicacion_retorno': 'Bodega TI',
            'ubicacion_entrega': 'Oficina', 'estado_fisico_origen': 'USADO',
            'estado_fisico_destino': 'NUEVO', 'accesorios_devueltos': [{'nombre': 'Cable', 'entregado': True}],
            'accesorios_entregados': [{'nombre': 'Adaptador', 'entregado': True}],
            'observaciones': 'Cambio con fallo documental',
        }, format='json')
    assert failed.status_code == 400, (failed.status_code, failed.data)
    new.refresh_from_db(); third.refresh_from_db()
    assert new.usuario_id == person.pk and new.estado == 'ASIGNADO'
    assert third.usuario_id is None and third.estado == 'STOCK'
    assert MovimientoActivo.objects.count() == count_before
    final = client.post('/api/movimientos/cambio/', {
        'activo_origen_id': new.pk, 'activo_destino_id': third.pk,
        'colaborador_id': person.pk, 'ubicacion_retorno': 'Bodega TI',
        'ubicacion_entrega': 'Oficina', 'estado_fisico_origen': 'USADO',
        'estado_fisico_destino': 'NUEVO', 'accesorios_devueltos': [{'nombre': 'Cable', 'entregado': True}],
        'accesorios_entregados': [{'nombre': 'Adaptador', 'entregado': True}],
        'observaciones': 'Cambio confirmado',
    }, format='json')
    assert final.status_code == 201, (final.status_code, final.data)
    assert int(final.data['salida']['acta']['folio'][-6:]) == last_folio + 1
    assert int(final.data['entrada']['acta']['folio'][-6:]) == last_folio + 2
    assert SecurityAuditLog.objects.filter(module='ACTIVOS_ITAM', object_id_text=str(new.pk)).count() == 2
    viewer = User.objects.create_user(username=f'cambio_view_{suffix}', password='temporary-only')
    viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
    client.force_authenticate(user=viewer)
    assert exchange(new, third).status_code == 403
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie__in=[f'C-OLD-{suffix}', f'C-NEW-{suffix}', f'C-THIRD-{suffix}']).exists()
print('ITAM préstamo/cambio: dos actas enlazadas, folios consecutivos y rollback completo OK')
