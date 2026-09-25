from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Anexo, Departamento, Equipamiento, IP, Usuario


class AssignmentStateConstraintTests(TestCase):
    def setUp(self):
        self.department = Departamento.objects.create(nombre='Restricciones')
        self.user = Usuario.objects.create(
            nombre_completo='Persona Restricciones',
            usuario_red='restricciones',
            correo_corp='restricciones@example.com',
            departamento=self.department,
        )

    def assert_update_rejected(self, update):
        with self.assertRaises(IntegrityError), transaction.atomic():
            update()

    def test_anexo_owner_and_state_cannot_be_desynchronized(self):
        available = Anexo.objects.create(numero_anexo='7100')
        assigned = Anexo.objects.create(
            numero_anexo='7101',
            usuario=self.user,
        )

        self.assertEqual(available.estado, 'DISPONIBLE')
        self.assertEqual(assigned.estado, 'ASIGNADO')
        self.assert_update_rejected(lambda: Anexo.objects.filter(
            pk=available.pk,
        ).update(estado='ASIGNADO'))
        self.assert_update_rejected(lambda: Anexo.objects.filter(
            pk=assigned.pk,
        ).update(estado='DISPONIBLE'))

    def test_equipment_owner_state_and_assignment_date_remain_coherent(self):
        stock = Equipamiento.objects.create(
            tipo='Notebook',
            marca='Dell',
            modelo='Latitude',
            numero_serie='STATE-STOCK-01',
            estado='ASIGNADO',
            fecha_asignacion=date(2026, 9, 25),
        )
        assigned = Equipamiento.objects.create(
            usuario=self.user,
            tipo='Celular',
            marca='Apple',
            modelo='iPhone',
            numero_serie='STATE-ASSIGNED-01',
            estado='STOCK',
            fecha_asignacion=date(2026, 9, 25),
        )

        self.assertEqual(stock.estado, 'STOCK')
        self.assertIsNone(stock.fecha_asignacion)
        self.assertEqual(assigned.estado, 'ASIGNADO')

        self.assert_update_rejected(lambda: Equipamiento.objects.filter(
            pk=stock.pk,
        ).update(estado='ASIGNADO'))
        self.assert_update_rejected(lambda: Equipamiento.objects.filter(
            pk=stock.pk,
        ).update(fecha_asignacion=date(2026, 9, 25)))
        self.assert_update_rejected(lambda: Equipamiento.objects.filter(
            pk=assigned.pk,
        ).update(estado='STOCK'))

    def test_ip_state_requires_exactly_one_legacy_owner_representation(self):
        free_ip = IP.objects.create(direccion_ip='172.24.1.210')
        user_ip = IP.objects.create(
            direccion_ip='172.24.1.211',
            usuario=self.user,
        )
        other_ip = IP.objects.create(
            direccion_ip='172.24.1.212',
            asignado_otro='  Impresora   Recepcion  ',
        )
        normalized_empty = IP.objects.create(
            direccion_ip='172.24.1.213',
            asignado_otro='   ',
        )

        self.assertEqual(free_ip.estado, 'LIBRE')
        self.assertEqual(user_ip.estado, 'RESERVADA')
        self.assertEqual(other_ip.estado, 'RESERVADA')
        self.assertEqual(other_ip.asignado_otro, 'Impresora Recepcion')
        self.assertEqual(normalized_empty.estado, 'LIBRE')
        self.assertIsNone(normalized_empty.asignado_otro)

        self.assert_update_rejected(lambda: IP.objects.filter(
            pk=free_ip.pk,
        ).update(estado='RESERVADA'))
        self.assert_update_rejected(lambda: IP.objects.filter(
            pk=user_ip.pk,
        ).update(estado='LIBRE'))
        self.assert_update_rejected(lambda: IP.objects.filter(
            pk=other_ip.pk,
        ).update(usuario=self.user))
