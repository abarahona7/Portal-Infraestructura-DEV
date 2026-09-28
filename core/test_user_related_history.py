from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import (
    Anexo,
    AsignacionIP,
    Departamento,
    Equipamiento,
    HistorialAsignacionIP,
    HistorialUsuario,
    IP,
    Usuario,
)


class UserRelatedHistoryTests(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.operator = User.objects.create_user(
            'audit-admin',
            password='StrongPass!123',
        )
        self.operator.groups.add(admin_group)
        self.client = APIClient()
        self.client.force_authenticate(self.operator)

        self.department = Departamento.objects.create(nombre='Tecnología')
        self.user = Usuario.objects.create(
            nombre_completo='Usuario Historial Relacionado',
            usuario_red='historial.relacionado',
            correo_corp='historial.relacionado@example.com',
            departamento=self.department,
            hostname='NB-HIST-01',
        )

    def test_ip_assignment_and_release_are_visible_in_both_histories(self):
        ip = IP.objects.create(direccion_ip='172.24.1.220')

        assigned = self.client.patch(
            f'/api/usuarios/{self.user.pk}/',
            {'ip_seleccionada': ip.direccion_ip},
            format='json',
        )
        self.assertEqual(assigned.status_code, 200)

        ip_history = HistorialAsignacionIP.objects.get(
            ip=ip,
            accion='ASIGNACION',
        )
        user_history = HistorialUsuario.objects.get(
            usuario=self.user,
            accion='ASIGNACION_IP',
        )
        self.assertEqual(ip_history.propietario_id, self.user.pk)
        self.assertEqual(ip_history.realizado_por, self.operator.username)
        self.assertEqual(user_history.modulo_relacionado, 'Gestión de IPs')
        self.assertEqual(user_history.objeto_relacionado_id, str(ip.pk))
        self.assertIn(ip.direccion_ip, user_history.observacion)
        self.assertEqual(user_history.modificado_por, self.operator.username)

        released = self.client.patch(
            f'/api/usuarios/{self.user.pk}/',
            {'ip_seleccionada': None},
            format='json',
        )
        self.assertEqual(released.status_code, 200)
        self.assertTrue(
            HistorialAsignacionIP.objects.filter(
                ip=ip,
                accion='LIBERACION',
            ).exists()
        )
        self.assertTrue(
            HistorialUsuario.objects.filter(
                usuario=self.user,
                accion='LIBERACION_IP',
                modulo_relacionado='Gestión de IPs',
                objeto_relacionado_id=str(ip.pk),
            ).exists()
        )

        detail = self.client.get(f'/api/usuarios/{self.user.pk}/')
        self.assertEqual(detail.status_code, 200)
        related_entries = [
            item
            for item in detail.json()['historial']
            if item['modulo_relacionado'] == 'Gestión de IPs'
        ]
        self.assertEqual(len(related_entries), 2)

    def test_equipment_and_extension_changes_are_linked_to_user_history(self):
        equipment = Equipamiento.objects.create(
            usuario=self.user,
            tipo='Notebook',
            marca='Lenovo',
            modelo='T14',
            numero_serie='REL-HIST-001',
            estado='ASIGNADO',
        )
        extension = Anexo.objects.create(
            numero_anexo='7788',
            usuario=self.user,
        )

        self.assertTrue(
            HistorialUsuario.objects.filter(
                usuario=self.user,
                accion='ASIGNACION_EQUIPO',
                modulo_relacionado='Equipos',
                objeto_relacionado_id=str(equipment.pk),
            ).exists()
        )
        self.assertTrue(
            HistorialUsuario.objects.filter(
                usuario=self.user,
                accion='ASIGNACION_ANEXO',
                modulo_relacionado='Anexos',
                objeto_relacionado_id=str(extension.pk),
            ).exists()
        )

        equipment.usuario = None
        equipment.save()
        extension.usuario = None
        extension.save()

        self.assertTrue(
            HistorialUsuario.objects.filter(
                usuario=self.user,
                accion='LIBERACION_EQUIPO',
            ).exists()
        )
        self.assertTrue(
            HistorialUsuario.objects.filter(
                usuario=self.user,
                accion='LIBERACION_ANEXO',
            ).exists()
        )

    def test_medical_leave_only_releases_ip(self):
        ip = IP.objects.create(
            direccion_ip='172.24.1.221',
            usuario=self.user,
        )
        equipment = Equipamiento.objects.create(
            usuario=self.user,
            tipo='Notebook',
            marca='HP',
            modelo='EliteBook',
            numero_serie='LIC-HIST-001',
            estado='ASIGNADO',
        )
        extension = Anexo.objects.create(
            numero_anexo='7799',
            usuario=self.user,
        )

        response = self.client.patch(
            f'/api/usuarios/{self.user.pk}/',
            {'estado': 'LICENCIA'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        ip.refresh_from_db()
        equipment.refresh_from_db()
        extension.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.user.estado, 'LICENCIA')
        self.assertEqual(ip.estado, 'LIBRE')
        self.assertIsNone(ip.usuario_id)
        self.assertFalse(AsignacionIP.objects.filter(ip=ip).exists())
        self.assertEqual(equipment.usuario_id, self.user.pk)
        self.assertEqual(equipment.estado, 'ASIGNADO')
        self.assertEqual(extension.usuario_id, self.user.pk)
        self.assertEqual(extension.estado, 'ASIGNADO')
        self.assertTrue(
            HistorialUsuario.objects.filter(
                usuario=self.user,
                accion='LIBERACION_IP',
            ).exists()
        )
        self.assertFalse(
            HistorialUsuario.objects.filter(
                usuario=self.user,
                accion__in=['LIBERACION_EQUIPO', 'LIBERACION_ANEXO'],
            ).exists()
        )


class DeliveryActValidationTests(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.operator = User.objects.create_user(
            'acta-admin',
            password='StrongPass!123',
        )
        self.operator.groups.add(admin_group)
        self.client = APIClient()
        self.client.force_authenticate(self.operator)
        department = Departamento.objects.create(nombre='Operaciones')
        self.user = Usuario.objects.create(
            nombre_completo='Usuario Sin Equipos',
            usuario_red='sin.equipos',
            correo_corp='sin.equipos@example.com',
            departamento=department,
        )

    @patch('core.views.generar_acta_entrega_pdf')
    def test_act_is_rejected_without_assigned_equipment(self, pdf_generator):
        response = self.client.get(
            f'/api/usuarios/{self.user.pk}/acta-entrega/'
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn('no tiene equipos o insumos asignados', response.json()['detail'])
        pdf_generator.assert_not_called()

    @patch('core.views.generar_acta_entrega_pdf', return_value=BytesIO(b'%PDF-test'))
    def test_act_is_generated_when_user_has_equipment(self, pdf_generator):
        Equipamiento.objects.create(
            usuario=self.user,
            tipo='Notebook',
            marca='Dell',
            modelo='Latitude',
            numero_serie='ACTA-REL-001',
            estado='ASIGNADO',
        )

        response = self.client.get(
            f'/api/usuarios/{self.user.pk}/acta-entrega/'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        pdf_generator.assert_called_once()
