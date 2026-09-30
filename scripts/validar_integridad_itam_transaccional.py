"""Ejecutar con `.venv/bin/python manage.py shell < scripts/validar_integridad_itam_transaccional.py`."""
import uuid
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from rest_framework.test import APIClient

from core.management.commands.validar_integridad_itam import verificar_integridad
from core.models import ActaEntrega, ActaEstadoEvento, Departamento, Equipamiento, MovimientoActivo, Usuario
from core.services.acta_estado_service import registrar_estado_acta

suffix = uuid.uuid4().hex[:10]
with transaction.atomic():
    departamento = Departamento.objects.create(nombre=f'Integridad ITAM {suffix}')
    persona = Usuario.objects.create(nombre_completo='Persona integridad', usuario_red=f'integridad.{suffix}',
        correo_corp=f'integridad.{suffix}@example.com', departamento=departamento, rut='11.111.111-1')
    operador = User.objects.create_user(username=f'integridad_op_{suffix}', password='temporal')
    operador.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
    activo = Equipamiento.objects.create(tipo='Notebook', marca='Prueba', modelo='Integridad',
        numero_serie=f'INT-{suffix}', estado='STOCK', accesorios='Cargador')
    cliente = APIClient(SERVER_NAME='127.0.0.1', HTTP_HOST='127.0.0.1')
    cliente.force_authenticate(user=operador)
    respuesta = cliente.post('/api/movimientos/', {
        'tipo_movimiento': 'PRESTAMO', 'activo_id': activo.pk,
        'colaborador_destino_id': persona.pk, 'ubicacion_destino': 'Oficina',
        'estado_fisico': 'USADO', 'accesorios_detalle': [{'nombre': 'Cargador', 'entregado': True}],
    }, format='json')
    assert respuesta.status_code == 201, (respuesta.status_code, respuesta.data)
    acta = ActaEntrega.objects.get(pk=respuesta.data['acta']['id'])
    registrar_estado_acta(acta_id=acta.pk, estado_nuevo='PENDIENTE_FIRMA', usuario=operador)
    pdf = bytes(acta.documento_pdf)
    registrar_estado_acta(acta_id=acta.pk, estado_nuevo='FIRMADA', usuario=operador,
        archivo_firmado=SimpleUploadedFile('firmada.pdf', pdf, content_type='application/pdf'))
    call_command('validar_integridad_itam', stdout=StringIO())
    call_command('validar_integridad_portal', stdout=StringIO())

    ActaEntrega.objects.create(
        folio='ATI-2099-000002', anio=2099, numero_correlativo=1,
        tipo_movimiento='ALTA', usuario_ti=operador, documento_pdf=b'%PDF-defectuoso',
        hash_verificacion='0' * 64, snapshot_documento={'folio': 'incorrecto'},
    )
    ActaEstadoEvento.objects.create(acta=acta, estado_anterior='GENERADA',
        estado_nuevo='CERRADA', usuario=operador)
    ActaEstadoEvento.objects.create(acta=acta, estado_anterior='CERRADA',
        estado_nuevo='FIRMADA', usuario=operador, copia_firmada_pdf=b'%PDF-falsa',
        hash_copia_firmada='0' * 64)
    MovimientoActivo.objects.create(activo=activo, acta=acta, tipo_movimiento='BAJA',
        ubicacion_destino='Bodega', estado_operativo_resultante='BAJA',
        ejecutado_por=operador.username, snapshot={})
    resultados = verificar_integridad(muestras=1)
    for codigo in ('folio_inconsistente', 'contador_desfasado', 'pdf_original_invalido',
                   'snapshot_documento_inconsistente', 'acta_movimientos_inconsistentes',
                   'movimiento_acta_inconsistente', 'evento_cadena_invalida',
                   'copia_firmada_invalida'):
        assert resultados[codigo]['cantidad'] > 0, (codigo, resultados[codigo])
    try:
        call_command('validar_integridad_itam', stdout=StringIO(), stderr=StringIO())
    except CommandError:
        pass
    else:
        raise AssertionError('El comando debe fallar al encontrar inconsistencias.')
    transaction.set_rollback(True)
assert not Equipamiento.objects.filter(numero_serie=f'INT-{suffix}').exists()
print('Integridad ITAM: préstamo y firma válidos; anomalías detectadas; rollback completo')
