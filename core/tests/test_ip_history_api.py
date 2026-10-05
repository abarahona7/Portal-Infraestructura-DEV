from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import HistorialAsignacionIP, IP


class IpHistoryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user(
            'ip-history-admin',
            password='StrongPass!123',
        )
        self.admin.groups.add(admin_group)
        self.client.force_authenticate(user=self.admin)
        self.ip = IP.objects.create(direccion_ip='172.24.1.230')

    def test_assignment_and_release_history_include_authenticated_actor(self):
        assigned = self.client.patch(
            f'/api/ips/{self.ip.pk}/',
            {'asignado_otro': 'Impresora Finanzas'},
            format='json',
        )
        self.assertEqual(assigned.status_code, 200)

        released = self.client.patch(
            f'/api/ips/{self.ip.pk}/',
            {'asignado_otro': None},
            format='json',
        )
        self.assertEqual(released.status_code, 200)

        records = HistorialAsignacionIP.objects.filter(ip=self.ip)
        self.assertEqual(records.count(), 2)
        self.assertFalse(
            records.exclude(realizado_por=self.admin.username).exists()
        )

        response = self.client.get(f'/api/ips/{self.ip.pk}/historial/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [entry['accion'] for entry in response.json()],
            ['LIBERACION', 'ASIGNACION'],
        )
        self.assertEqual(
            response.json()[0]['propietario_nombre'],
            'Impresora Finanzas',
        )
        self.assertEqual(
            response.json()[0]['realizado_por'],
            self.admin.username,
        )
