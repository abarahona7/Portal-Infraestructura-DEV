from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Anexo, Departamento, Equipamiento, HistorialUsuario, IP, RevisionBajaUsuario, Usuario


class RevisionBajaTests(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        operator_group, _ = Group.objects.get_or_create(name='Operador Infraestructura')
        viewer_group, _ = Group.objects.get_or_create(name='Visualizador')
        self.admin = User.objects.create_user('revision-admin', password='TestPass!123')
        self.admin.groups.add(admin_group)
        self.operator = User.objects.create_user('revision-operator', password='TestPass!123')
        self.operator.groups.add(operator_group)
        self.viewer = User.objects.create_user('revision-viewer', password='TestPass!123')
        self.viewer.groups.add(viewer_group)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        department = Departamento.objects.create(nombre='Tecnología')
        self.usuario = Usuario.objects.create(
            nombre_completo='Persona de Revisión', usuario_red='revision.user',
            correo_corp='revision@example.com', departamento=department,
        )

    def test_one_shared_review_contains_all_released_resources_and_is_logged(self):
        notebook = Equipamiento.objects.create(
            usuario=self.usuario, tipo='Notebook', marca='Lenovo', modelo='T14', numero_serie='REV-1',
        )
        phone = Equipamiento.objects.create(
            usuario=self.usuario, tipo='Celular', marca='Apple', modelo='iPhone', numero_serie='REV-2',
        )
        ip = IP.objects.create(direccion_ip='172.23.1.233', estado='RESERVADA', usuario=self.usuario)
        anexo = Anexo.objects.create(numero_anexo='5788', usuario=self.usuario)
        url = f'/api/usuarios/{self.usuario.pk}/'
        checks = [item['id'] for item in self.client.get(url).data['protocolos_estado']['BAJA']]
        self.assertEqual(set(checks), {'equipos', 'ip', 'anexo'})
        failed = self.client.patch(url, {'estado': 'BAJA'}, format='json')
        self.assertEqual(failed.status_code, 400)
        self.assertFalse(RevisionBajaUsuario.objects.exists())

        response = self.client.patch(url, {'estado': 'BAJA', 'protocolo_confirmaciones': checks}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        notebook.refresh_from_db(); phone.refresh_from_db(); ip.refresh_from_db(); anexo.refresh_from_db()
        self.assertIsNone(notebook.usuario_id)
        self.assertIsNone(phone.usuario_id)
        self.assertIsNone(ip.usuario_id)
        self.assertIsNone(anexo.usuario_id)
        revision = RevisionBajaUsuario.objects.get()
        self.assertEqual(revision.motivo, 'BAJA')
        self.assertEqual({r['clave'] for r in revision.recursos}, {
            f'equipo:{notebook.pk}', f'equipo:{phone.pk}', f'ip:{ip.pk}', f'anexo:{anexo.pk}',
        })
        self.assertEqual(revision.creado_por, self.admin.username)
        self.assertTrue(HistorialUsuario.objects.filter(usuario=self.usuario, accion='REVISION_BAJA_PENDIENTE').exists())
        self.assertEqual(self.client.get('/api/revisiones-baja/').data['pendientes'], 1)

        self.client.force_authenticate(self.operator)
        confirm_url = f'/api/revisiones-baja/{revision.pk}/confirmar/'
        self.assertEqual(self.client.post(confirm_url, {'confirmaciones': [revision.recursos[0]['clave']]}, format='json').status_code, 400)
        self.assertEqual(self.client.post(confirm_url, {
            'confirmaciones': [r['clave'] for r in revision.recursos],
        }, format='json').status_code, 200)
        revision.refresh_from_db()
        self.assertEqual(revision.revisado_por, self.operator.username)
        self.assertIsNotNone(revision.revisado_en)
        self.assertEqual(self.client.get('/api/revisiones-baja/').data['pendientes'], 0)
        self.assertEqual(self.client.post(confirm_url, {'confirmaciones': []}, format='json').status_code, 409)
        self.assertTrue(HistorialUsuario.objects.filter(usuario=self.usuario, accion='REVISION_BAJA_CONFIRMADA', modificado_por=self.operator.username).exists())

    def test_no_alert_without_resources_and_no_duplicate_on_later_edit(self):
        url = f'/api/usuarios/{self.usuario.pk}/'
        self.assertEqual(self.client.patch(url, {
            'estado': 'BAJA', 'protocolo_confirmaciones': ['sin_recursos'],
        }, format='json').status_code, 200)
        self.assertFalse(RevisionBajaUsuario.objects.exists())
        self.assertEqual(self.client.patch(url, {'cargo': 'Analista'}, format='json').status_code, 200)
        self.assertFalse(RevisionBajaUsuario.objects.exists())

    def test_licencia_creates_review_only_for_released_ip(self):
        notebook = Equipamiento.objects.create(
            usuario=self.usuario, tipo='Notebook', marca='Lenovo', modelo='T14', numero_serie='REV-LIC-1',
        )
        anexo = Anexo.objects.create(numero_anexo='5799', usuario=self.usuario)
        ip = IP.objects.create(direccion_ip='172.23.1.234', estado='RESERVADA', usuario=self.usuario)
        url = f'/api/usuarios/{self.usuario.pk}/'
        checks = [item['id'] for item in self.client.get(url).data['protocolos_estado']['LICENCIA']]
        self.assertEqual(set(checks), {'ip', 'custodia'})
        response = self.client.patch(url, {
            'estado': 'LICENCIA', 'protocolo_confirmaciones': checks,
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        notebook.refresh_from_db(); anexo.refresh_from_db(); ip.refresh_from_db()
        self.assertEqual(notebook.usuario_id, self.usuario.pk)
        self.assertEqual(anexo.usuario_id, self.usuario.pk)
        self.assertIsNone(ip.usuario_id)
        revision = RevisionBajaUsuario.objects.get()
        self.assertEqual(revision.motivo, 'LICENCIA')
        self.assertEqual([r['clave'] for r in revision.recursos], [f'ip:{ip.pk}'])
        self.assertTrue(HistorialUsuario.objects.filter(usuario=self.usuario, accion='REVISION_LICENCIA_PENDIENTE').exists())
        self.assertEqual(self.client.get('/api/revisiones-baja/').data['pendientes'], 1)
        self.assertEqual(self.client.patch(url, {'cargo': 'Analista'}, format='json').status_code, 200)
        self.assertEqual(RevisionBajaUsuario.objects.count(), 1)
        self.client.force_authenticate(self.operator)
        self.assertEqual(self.client.post(f'/api/revisiones-baja/{revision.pk}/confirmar/', {
            'confirmaciones': [f'ip:{ip.pk}'],
        }, format='json').status_code, 200)
        self.assertTrue(HistorialUsuario.objects.filter(usuario=self.usuario, accion='REVISION_LICENCIA_CONFIRMADA').exists())

    def test_licencia_without_ip_does_not_create_review(self):
        notebook = Equipamiento.objects.create(
            usuario=self.usuario, tipo='Notebook', marca='Lenovo', modelo='T14', numero_serie='REV-LIC-2',
        )
        url = f'/api/usuarios/{self.usuario.pk}/'
        checks = [item['id'] for item in self.client.get(url).data['protocolos_estado']['LICENCIA']]
        self.assertEqual(checks, ['custodia'])
        self.assertEqual(self.client.patch(url, {
            'estado': 'LICENCIA', 'protocolo_confirmaciones': checks,
        }, format='json').status_code, 200)
        notebook.refresh_from_db()
        self.assertEqual(notebook.usuario_id, self.usuario.pk)
        self.assertFalse(RevisionBajaUsuario.objects.exists())

    def test_viewer_cannot_read_or_confirm_review(self):
        revision = RevisionBajaUsuario.objects.create(
            usuario=self.usuario, usuario_nombre=self.usuario.nombre_completo,
            usuario_red=self.usuario.usuario_red,
            recursos=[{'clave': 'ip:1', 'tipo': 'ip', 'id': 1, 'nombre': '172.23.1.1'}],
        )
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get('/api/revisiones-baja/').status_code, 403)
        self.assertEqual(self.client.post(f'/api/revisiones-baja/{revision.pk}/confirmar/', {
            'confirmaciones': ['ip:1'],
        }, format='json').status_code, 403)
