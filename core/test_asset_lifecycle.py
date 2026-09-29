"""Integration checks for the asset transaction and its persisted evidence."""
import hashlib

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import (ActaEntrega, Departamento, Equipamiento, FolioContador,
                         MovimientoActivo, SecurityAuditLog, Usuario)
from core.rut_validator import validar_rut


class AssetLifecycleTests(TestCase):
    def setUp(self):
        department = Departamento.objects.create(nombre='TI Activos')
        self.person = Usuario.objects.create(
            nombre_completo='Persona Activos', usuario_red='persona.activos',
            correo_corp='persona.activos@example.com', departamento=department,
            rut='12.345.678-5',
        )
        self.actor = User.objects.create_user(username='operador_activos', password='strong-password')
        self.actor.groups.add(Group.objects.get_or_create(name='Operador Infraestructura')[0])
        self.asset = Equipamiento.objects.create(
            tipo='Notebook', marca='Lenovo', modelo='T14', numero_serie='ITAM-T14-1',
            estado='STOCK', accesorios='Cargador, Mouse', ubicacion_actual='Bodega TI',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.actor)

    def _assign(self):
        return self.client.post('/api/movimientos/', {
            'tipo_movimiento': 'ASIGNACION', 'activo_id': self.asset.pk,
            'colaborador_destino_id': self.person.pk, 'ubicacion_destino': 'Oficina TI',
            'estado_fisico': 'USADO', 'accesorios_detalle': [
                {'nombre': 'Cargador', 'entregado': True},
                {'nombre': 'Mouse', 'entregado': True},
            ], 'observaciones': 'Equipo comprobado',
        }, format='json')

    def test_assignment_and_return_persist_unique_pdfs_and_history(self):
        first = self._assign()
        self.assertEqual(first.status_code, 201, first.data)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.usuario_id, self.person.pk)
        self.assertEqual(self.asset.estado, 'ASIGNADO')
        first_folio = first.data['acta']['folio']
        self.assertRegex(first_folio, r'^ATI-\d{4}-000001$')
        pdf = self.client.get(f"/api/actas/{first.data['acta']['id']}/pdf/")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF-'))
        self.assertEqual(hashlib.sha256(pdf.content).hexdigest(), first.data['acta']['hash_verificacion'])
        self.assertEqual(self._assign().status_code, 409)
        self.assertEqual(MovimientoActivo.objects.count(), 1)
        missing = self.client.post('/api/movimientos/', {
            'tipo_movimiento': 'DEVOLUCION', 'activo_id': self.asset.pk,
            'colaborador_origen_id': self.person.pk, 'ubicacion_destino': 'Bodega TI',
            'estado_fisico': 'USADO', 'accesorios_detalle': [{'nombre': 'Cargador', 'entregado': True}],
        }, format='json')
        self.assertEqual(missing.status_code, 400, missing.data)
        returned = self.client.post('/api/movimientos/', {
            'tipo_movimiento': 'DEVOLUCION', 'activo_id': self.asset.pk,
            'colaborador_origen_id': self.person.pk, 'ubicacion_destino': 'Bodega TI',
            'estado_fisico': 'USADO', 'accesorios_detalle': [
                {'nombre': 'Cargador', 'entregado': True},
                {'nombre': 'Mouse', 'entregado': False, 'nota': 'Extraviado'},
            ],
        }, format='json')
        self.assertEqual(returned.status_code, 201, returned.data)
        self.assertNotEqual(returned.data['acta']['folio'], first_folio)
        self.asset.refresh_from_db()
        self.assertIsNone(self.asset.usuario_id)
        self.assertEqual(self.asset.estado, 'STOCK')
        self.assertEqual(FolioContador.objects.get(tipo_documento='ATI').ultimo_folio, 2)
        self.assertEqual(SecurityAuditLog.objects.filter(module='ACTIVOS_ITAM').count(), 2)
        history = self.client.get(f'/api/movimientos/?activo_id={self.asset.pk}')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data['count'], 2)
        self.assertEqual(history.data['results'][1]['acta']['folio'], first_folio)
        acta = ActaEntrega.objects.get(folio=first_folio)
        self.assertEqual(acta.snapshot_documento['activo']['numero_serie'], 'ITAM-T14-1')
        with self.assertRaises(ValidationError):
            acta.delete()
        with self.assertRaises(ValidationError):
            MovimientoActivo.objects.update(observaciones='Manipulado')
        self.assertEqual(self.client.delete(f"/api/movimientos/{first.data['id']}/").status_code, 403)

    def test_rut_validation(self):
        self.assertEqual(validar_rut('12.345.678-5'), '12345678-5')
        with self.assertRaises(ValidationError):
            validar_rut('12.345.678-9')

    def test_viewer_cannot_create_movement(self):
        viewer = User.objects.create_user('viewer_itam', password='strong-password')
        viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
        self.client.force_authenticate(user=viewer)
        self.assertEqual(self._assign().status_code, 403)
