from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from core.audit import reset_current_audit_user, set_current_audit_user
from core.models import HistorialServidor, IP, Servidor
from core.services.papelera import archive_record


class ServerHistoryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user(
            'server-history-admin',
            password='StrongPass!123',
        )
        self.admin.groups.add(admin_group)
        self.client.force_authenticate(user=self.admin)
        self.first_ip = IP.objects.create(direccion_ip='172.23.1.230')
        self.second_ip = IP.objects.create(direccion_ip='172.23.1.231')

    def create_server(self):
        response = self.client.post(
            '/api/servidores/',
            {
                'ip': self.first_ip.direccion_ip,
                'hostname': 'SRV-HISTORY-01',
                'descripcion': 'Servidor inicial',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def test_create_and_update_are_audited_and_exposed_in_detail(self):
        server_id = self.create_server()

        created_history = HistorialServidor.objects.get(
            servidor_id=server_id,
            accion='CREACION',
        )
        self.assertEqual(created_history.modificado_por, self.admin.username)
        self.assertEqual(created_history.servidor_hostname, 'SRV-HISTORY-01')

        updated = self.client.patch(
            f'/api/servidores/{server_id}/',
            {
                'ip': self.second_ip.direccion_ip,
                'hostname': 'SRV-HISTORY-02',
                'descripcion': 'Servidor actualizado',
            },
            format='json',
        )
        self.assertEqual(updated.status_code, 200)

        changed_history = HistorialServidor.objects.get(
            servidor_id=server_id,
            accion='MODIFICACION',
        )
        self.assertEqual(changed_history.modificado_por, self.admin.username)
        self.assertIn('Hostname:::SRV-HISTORY-01:::SRV-HISTORY-02', changed_history.observacion)
        self.assertIn('DirecciÃ³n IP:::172.23.1.230:::172.23.1.231', changed_history.observacion)
        self.assertIn('DescripciÃ³n:::Servidor inicial:::Servidor actualizado', changed_history.observacion)

        detail = self.client.get(f'/api/servidores/{server_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['ip'], self.second_ip.direccion_ip)
        self.assertEqual(
            [entry['accion'] for entry in detail.json()['historial']],
            ['MODIFICACION', 'CREACION'],
        )

    def test_technical_archive_is_audited_and_releases_ip(self):
        server_id = self.create_server()

        self.assertEqual(self.client.delete(f'/api/servidores/{server_id}/').status_code, 403)
        token = set_current_audit_user(self.admin)
        try:
            archive_record(Servidor.objects.get(pk=server_id), reason='Solicitud técnica')
        finally:
            reset_current_audit_user(token)
        self.assertFalse(Servidor.objects.filter(pk=server_id).exists())
        self.first_ip.refresh_from_db()
        self.assertEqual(self.first_ip.estado, 'LIBRE')
        self.assertIsNone(self.first_ip.asignado_otro)
        deletion_history = HistorialServidor.objects.get(
            servidor_id=server_id,
            accion='ARCHIVO',
            servidor_hostname='SRV-HISTORY-01',
        )
        self.assertEqual(deletion_history.modificado_por, self.admin.username)
        self.assertIn('Dirección IP:::172.23.1.230:::Liberada', deletion_history.observacion)
