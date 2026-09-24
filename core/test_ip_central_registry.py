from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import (
    AsignacionIP,
    HistorialAsignacionIP,
    IP,
    TipoAsignacionIP,
    Usuario,
)
from core.serializers import IPSerializer
from core.services.asignacion_ips import assign_ip_to_user


class IpCentralRegistryTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create(
            nombre_completo='Usuario Registro IP',
            usuario_red='registro.ip',
            correo_corp='registro.ip@example.com',
        )
        self.first_ip = IP.objects.create(direccion_ip='172.24.1.220')
        self.second_ip = IP.objects.create(direccion_ip='172.24.1.221')

    def test_manual_assignment_is_registered_and_audited(self):
        self.first_ip.asignado_otro = 'Impresora Finanzas'
        self.first_ip.save()

        assignment = AsignacionIP.objects.get(ip=self.first_ip)
        self.first_ip.refresh_from_db()
        self.assertEqual(assignment.tipo, TipoAsignacionIP.OTRO)
        self.assertEqual(assignment.detalle, 'Impresora Finanzas')
        self.assertEqual(self.first_ip.estado, 'RESERVADA')
        self.assertTrue(
            HistorialAsignacionIP.objects.filter(
                ip=self.first_ip,
                accion='ASIGNACION',
                propietario_nombre='Impresora Finanzas',
            ).exists()
        )

        self.first_ip.asignado_otro = None
        self.first_ip.save()

        self.first_ip.refresh_from_db()
        self.assertFalse(AsignacionIP.objects.filter(ip=self.first_ip).exists())
        self.assertEqual(self.first_ip.estado, 'LIBRE')
        self.assertTrue(
            HistorialAsignacionIP.objects.filter(
                ip=self.first_ip,
                accion='LIBERACION',
                propietario_nombre='Impresora Finanzas',
            ).exists()
        )

    def test_user_change_keeps_one_active_assignment(self):
        assign_ip_to_user(self.user.pk, self.first_ip.direccion_ip)
        assign_ip_to_user(self.user.pk, self.second_ip.direccion_ip)

        assignment = AsignacionIP.objects.get(usuario=self.user)
        self.first_ip.refresh_from_db()
        self.second_ip.refresh_from_db()
        self.assertEqual(assignment.ip_id, self.second_ip.pk)
        self.assertEqual(assignment.tipo, TipoAsignacionIP.USUARIO)
        self.assertEqual(self.first_ip.estado, 'LIBRE')
        self.assertEqual(self.second_ip.estado, 'RESERVADA')
        self.assertEqual(
            HistorialAsignacionIP.objects.filter(
                direccion_ip=self.first_ip.direccion_ip,
                accion='LIBERACION',
            ).count(),
            1,
        )

        serialized = IPSerializer(
            IP.objects.select_related(
                'asignacion_activa__usuario'
            ).get(pk=self.second_ip.pk)
        ).data
        self.assertEqual(serialized['tipo_asignacion'], 'USUARIO')
        self.assertEqual(serialized['asignado_a'], self.user.nombre_completo)

    def test_database_rejects_assignment_without_matching_owner(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AsignacionIP.objects.create(
                ip=self.first_ip,
                tipo=TipoAsignacionIP.USUARIO,
                detalle='Propietario inválido',
            )
