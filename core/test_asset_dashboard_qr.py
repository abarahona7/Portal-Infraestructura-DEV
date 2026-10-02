"""Contratos del tablero y la ficha QR que deben mantenerse en producción."""

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Departamento, Equipamiento, Usuario


@override_settings(PORTAL_PUBLIC_URL='https://portal.example.cl', IS_PRODUCTION=True)
class AssetDashboardQrTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('asset-admin', password='TestPassword123!')
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.department = Departamento.objects.create(nombre='Tecnología')
        self.other_department = Departamento.objects.create(nombre='Ventas')
        self.person = Usuario.objects.create(
            nombre_completo='Persona Activa', usuario_red='activa',
            correo_corp='activa@example.com', departamento=self.department,
        )
        self.inactive = Usuario.objects.create(
            nombre_completo='Persona Inactiva', usuario_red='inactiva',
            correo_corp='inactiva@example.com', departamento=self.other_department,
            estado='BAJA',
        )
        self.assigned = Equipamiento.objects.create(
            usuario=self.person, tipo='Notebook', marca='HP', modelo='840',
            numero_serie='QR-001', af='1001', estado='ASIGNADO',
        )
        self.unassigned = Equipamiento.objects.create(
            tipo='Notebook', marca='Dell', modelo='5420', estado='STOCK',
        )
        self.inactive_asset = Equipamiento.objects.create(
            usuario=self.inactive, tipo='Celular', marca='Samsung', modelo='A1',
            numero_serie='QR-002', estado='ASIGNADO',
        )

    def test_dashboard_counts_match_clickable_filters_and_departments(self):
        response = self.client.get('/api/activos/resumen/')
        self.assertEqual(response.status_code, 200)
        counts = response.data['conteos']
        self.assertEqual(counts['total'], 3)
        self.assertEqual(counts['asignados'], 2)
        self.assertEqual(counts['disponibles'], 1)
        self.assertEqual(
            {row['nombre']: row['total'] for row in response.data['departamentos']},
            {'Tecnología': 1, 'Ventas': 1},
        )
        for reason in ('sin_serie', 'sin_activo_fijo', 'sin_custodio', 'custodio_no_activo'):
            filtered = self.client.get('/api/equipos/', {'pendiente': reason})
            self.assertEqual(filtered.status_code, 200)
            self.assertEqual(filtered.data['count'], counts[reason])
        department_assets = self.client.get(
            '/api/equipos/', {'departamento_id': self.department.pk},
        )
        self.assertEqual(department_assets.data['count'], 1)
        self.assertEqual(department_assets.data['results'][0]['id'], self.assigned.pk)

    def test_qr_follows_assignment_without_exposing_secret_or_removed_fields(self):
        token = self.assigned.token_qr
        path = f'/api/activos/qr/{token}/'
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['qr_url'], f'https://portal.example.cl/qr/a/{token}')
        self.assertEqual(response.data['equipo']['departamento'], 'Tecnología')
        self.assertEqual(response.data['equipo']['usuario_nombre'], 'Persona Activa')
        for field in ('rut', 'ubicacion_actual', 'pin', 'icloud_password'):
            self.assertNotIn(field, response.data['equipo'])
        image = self.client.get(f'{path}imagen/')
        self.assertEqual(image.status_code, 200)
        self.assertTrue(image.content.startswith(b'<?xml'))
        self.assertEqual(image['Cache-Control'], 'no-store, private')

        self.assigned.usuario = None
        self.assigned.estado = 'STOCK'
        self.assigned.save()
        self.assigned.refresh_from_db()
        self.assertEqual(self.assigned.token_qr, token)
        unassigned_detail = self.client.get(path)
        self.assertIsNone(unassigned_detail.data['equipo']['departamento'])
        self.assertIsNone(unassigned_detail.data['equipo']['usuario_nombre'])

    def test_qr_requires_an_authorized_role(self):
        path = f'/api/activos/qr/{self.assigned.token_qr}/'
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get(path).status_code, (401, 403))
        viewer = User.objects.create_user('asset-viewer', password='TestPassword123!')
        viewer.groups.add(Group.objects.get_or_create(name='Visualizador')[0])
        self.client.force_authenticate(user=viewer)
        self.assertEqual(self.client.get(path).status_code, 403)

    @override_settings(PORTAL_PUBLIC_URL='http://portal.example.cl')
    def test_qr_rejects_http_url_in_production(self):
        path = f'/api/activos/qr/{self.assigned.token_qr}/'
        self.assertEqual(self.client.get(path).status_code, 503)
        self.assertEqual(self.client.get(f'{path}imagen/').status_code, 503)
