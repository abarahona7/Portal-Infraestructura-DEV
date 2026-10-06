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

    def test_ficha_interna_del_equipo_muestra_departamento_sin_depender_del_qr(self):
        assigned = self.client.get(f'/api/equipos/{self.assigned.pk}/')
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.data['departamento_nombre'], 'Tecnología')
        self.assertEqual(assigned.data['usuario_nombre'], 'Persona Activa')

        stock = self.client.get(f'/api/equipos/{self.unassigned.pk}/')
        self.assertEqual(stock.status_code, 200)
        self.assertIsNone(stock.data['departamento_nombre'])
        self.assertIsNone(stock.data.get('usuario_nombre'))

    def test_tipo_de_equipo_debe_corresponder_a_categoria_de_creacion_y_edicion(self):
        wrong_create = self.client.post('/api/equipos/?categoria=Notebook', {
            'tipo': 'Celular', 'marca': 'Samsung', 'modelo': 'A2',
        }, format='json')
        self.assertEqual(wrong_create.status_code, 400)
        self.assertIn('tipo', wrong_create.data)

        wrong_edit = self.client.patch(
            f'/api/equipos/{self.assigned.pk}/?categoria=Notebook',
            {'tipo': 'Mouse'}, format='json',
        )
        self.assertEqual(wrong_edit.status_code, 400)
        self.assertIn('tipo', wrong_edit.data)
        self.assigned.refresh_from_db()
        self.assertEqual(self.assigned.tipo, 'Notebook')

        wrong_peripheral = self.client.post('/api/equipos/?categoria=PERIFERICOS', {
            'tipo': 'Mac', 'marca': 'Apple', 'modelo': 'Mini',
        }, format='json')
        self.assertEqual(wrong_peripheral.status_code, 400)
        self.assertIn('tipo', wrong_peripheral.data)

        valid_peripheral = self.client.post('/api/equipos/?categoria=PERIFERICOS', {
            'tipo': 'Mouse', 'marca': 'Logitech', 'modelo': 'M100', 'estado': 'STOCK',
        }, format='json')
        self.assertEqual(valid_peripheral.status_code, 201)

    def test_mobile_numbers_follow_device_category_and_cannot_be_shared_across_users(self):
        second_person = Usuario.objects.create(
            nombre_completo='Persona Dos', usuario_red='persona.dos',
            correo_corp='persona.dos@example.com', departamento=self.other_department,
        )
        for index, category in enumerate(('Celular', 'Tablet', 'BAM / Router'), start=1):
            number = f'+5691234567{index}'
            created = self.client.post(f'/api/equipos/?categoria={category}', {
                'tipo': category, 'marca': 'Marca', 'modelo': 'Modelo',
                'numero_telefono': number, 'usuario': self.person.pk,
            }, format='json')
            self.assertEqual(created.status_code, 201, created.data)
            conflict = self.client.post(f'/api/equipos/?categoria={category}', {
                'tipo': category, 'marca': 'Otra', 'modelo': 'Modelo',
                'numero_telefono': number, 'usuario': second_person.pk,
            }, format='json')
            self.assertEqual(conflict.status_code, 400)
            self.assertIn('numero_telefono', conflict.data)

        invalid = self.client.post('/api/equipos/?categoria=Notebook', {
            'tipo': 'Notebook', 'marca': 'Dell', 'modelo': 'XPS',
            'numero_telefono': '+56999999999',
        }, format='json')
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('numero_telefono', invalid.data)

    def test_equipment_on_medical_leave_can_be_edited_but_not_newly_assigned(self):
        license_user = Usuario.objects.create(
            nombre_completo='Persona Licencia', usuario_red='licencia',
            correo_corp='licencia@example.com', departamento=self.department,
            estado='LICENCIA',
        )
        equipment = Equipamiento.objects.create(
            usuario=license_user, tipo='Tablet', marca='Samsung', modelo='Tab A',
            estado='ASIGNADO',
        )
        edit = self.client.patch(
            f'/api/equipos/{equipment.pk}/?categoria=Tablet',
            {'modelo': 'Tab S'}, format='json',
        )
        self.assertEqual(edit.status_code, 200, edit.data)
        self.assertEqual(edit.data['modelo'], 'Tab S')

        new_assignment = self.client.patch(
            f'/api/equipos/{self.unassigned.pk}/?categoria=Notebook',
            {'usuario': license_user.pk}, format='json',
        )
        self.assertEqual(new_assignment.status_code, 400)
        self.assertIn('usuario', new_assignment.data)

    def test_each_equipment_section_keeps_type_assignment_and_department(self):
        for category, equipment_type in (
            ('Notebook', 'Notebook'),
            ('Celular', 'Celular'),
            ('Tablet', 'Tablet'),
            ('Mac', 'Mac'),
            ('BAM / Router', 'BAM / Router'),
            ('PERIFERICOS', 'Monitor'),
        ):
            with self.subTest(category=category):
                created = self.client.post(f'/api/equipos/?categoria={category}', {
                    'tipo': equipment_type, 'marca': 'Marca', 'modelo': 'Modelo',
                    'usuario': self.person.pk,
                }, format='json')
                self.assertEqual(created.status_code, 201, created.data)
                self.assertEqual(created.data['estado'], 'ASIGNADO')
                self.assertEqual(created.data['departamento_nombre'], 'Tecnología')
                self.assertTrue(created.data['token_qr'])

                changed = self.client.patch(
                    f"/api/equipos/{created.data['id']}/?categoria={category}",
                    {'modelo': 'Modelo actualizado'}, format='json',
                )
                self.assertEqual(changed.status_code, 200, changed.data)
                self.assertEqual(changed.data['tipo'], equipment_type)
                self.assertEqual(changed.data['modelo'], 'Modelo actualizado')

    @override_settings(PORTAL_PUBLIC_URL='http://portal.example.cl')
    def test_qr_rejects_http_url_in_production(self):
        path = f'/api/activos/qr/{self.assigned.token_qr}/'
        self.assertEqual(self.client.get(path).status_code, 503)
        self.assertEqual(self.client.get(f'{path}imagen/').status_code, 503)
