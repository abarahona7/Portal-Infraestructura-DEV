from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import IP


class CompleteIpSegmentsCommandTests(TestCase):
    def test_creates_all_hosts_without_overwriting_existing_ip(self):
        existing = IP.objects.create(
            direccion_ip='172.24.1.10',
            estado='RESERVADA',
            asignado_otro='Equipo de red',
        )

        call_command('completar_segmentos_ip', '--apply', stdout=StringIO())

        self.assertEqual(
            IP.objects.filter(direccion_ip__startswith='172.24.1.').count(),
            254,
        )
        self.assertEqual(
            IP.objects.filter(direccion_ip__startswith='192.168.30.').count(),
            254,
        )
        self.assertFalse(IP.objects.filter(direccion_ip__endswith='.0').exists())
        self.assertFalse(IP.objects.filter(direccion_ip__endswith='.255').exists())

        existing.refresh_from_db()
        self.assertEqual(existing.estado, 'RESERVADA')
        self.assertEqual(existing.asignado_otro, 'Equipo de red')

        call_command('completar_segmentos_ip', '--apply', stdout=StringIO())
        self.assertEqual(IP.objects.count(), 508)
