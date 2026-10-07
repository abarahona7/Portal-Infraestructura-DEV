"""Casos límite de IP, Servidores y resumen de activos."""

from uuid import uuid4

from django.contrib.auth.models import Group, User
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import (
    AsignacionIP,
    Departamento,
    Equipamiento,
    HistorialAsignacionIP,
    IP,
    PCGenerico,
    Usuario,
)


class QAIpServidorTests(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user('qa-ip-admin', password='TestPassword123!')
        self.admin.groups.add(admin_group)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_servidor_rechaza_ip_ausente_red_broadcast_y_ocupada(self):
        self.assertEqual(self.client.post(
            '/api/servidores/', {'hostname': 'SRV-SIN-IP'}, format='json',
        ).status_code, 400)
        for suffix in ('0', '255'):
            with self.subTest(suffix=suffix):
                ip = IP.objects.create(direccion_ip=f'172.23.1.{suffix}')
                response = self.client.post(
                    '/api/servidores/',
                    {'hostname': f'SRV-LIMITE-{suffix}', 'ip': ip.direccion_ip},
                    format='json',
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn('ip', response.data)
                ip.refresh_from_db()
                self.assertEqual(ip.estado, 'LIBRE')
                self.assertFalse(AsignacionIP.objects.filter(ip=ip).exists())

        occupied = IP.objects.create(
            direccion_ip='172.23.1.243', asignado_otro='Impresora QA',
        )
        response = self.client.post(
            '/api/servidores/',
            {'hostname': 'SRV-OCUPADO', 'ip': occupied.direccion_ip},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(AsignacionIP.objects.filter(ip=occupied).exists())

    def test_admin_no_borra_ip_de_otro_uso_servidor_o_pc(self):
        department = Departamento.objects.create(nombre='Red QA')
        other = IP.objects.create(
            direccion_ip='172.23.1.244', asignado_otro='Cámara QA',
        )
        server_ip = IP.objects.create(direccion_ip='172.23.1.245')
        server = self.client.post(
            '/api/servidores/',
            {'hostname': 'SRV-QA-BORRADO', 'ip': server_ip.direccion_ip},
            format='json',
        )
        self.assertEqual(server.status_code, 201)
        pc_ip = IP.objects.create(direccion_ip='172.23.1.246')
        pc = self.client.post(
            '/api/pcs-genericos/',
            {'usuario_local': 'pc-qa', 'hostname': 'PC-QA-BORRADO',
             'departamento': department.pk, 'ip_seleccionada': pc_ip.direccion_ip},
            format='json',
        )
        self.assertEqual(pc.status_code, 201)

        for ip in (other, server_ip, pc_ip):
            with self.subTest(ip=ip.direccion_ip):
                self.assertEqual(self.client.delete(f'/api/ips/{ip.pk}/').status_code, 400)
                self.assertTrue(IP.objects.filter(pk=ip.pk).exists())
                self.assertTrue(AsignacionIP.objects.filter(ip=ip).exists())

    def test_borrado_directo_por_orm_conserva_asignacion_activa(self):
        ip = IP.objects.create(
            direccion_ip='172.23.1.247', asignado_otro='Equipo de prueba QA',
        )
        assignment_id = ip.asignacion_activa.pk
        history_count = HistorialAsignacionIP.objects.filter(ip=ip).count()
        self.assertGreater(history_count, 0)

        with self.assertRaises(ProtectedError):
            ip.delete()

        self.assertTrue(IP.objects.filter(pk=ip.pk).exists())
        self.assertTrue(AsignacionIP.objects.filter(pk=assignment_id).exists())
        self.assertEqual(HistorialAsignacionIP.objects.filter(ip=ip).count(), history_count)

    def test_brecha_5_no_debe_borrar_ip_reservada_aunque_falte_asignacion_central(self):
        ip = IP.objects.create(
            direccion_ip='172.23.1.248', asignado_otro='Reserva heredada QA',
        )
        AsignacionIP.objects.filter(ip=ip).delete()
        ip.refresh_from_db()
        self.assertEqual(ip.estado, 'RESERVADA')
        self.assertFalse(AsignacionIP.objects.filter(ip=ip).exists())

        response = self.client.delete(f'/api/ips/{ip.pk}/')

        self.assertEqual(response.status_code, 400)
        self.assertTrue(IP.objects.filter(pk=ip.pk).exists())


@override_settings(PORTAL_PUBLIC_URL='https://portal.qa.example.cl')
class QAResumenActivosTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('qa-assets-admin', password='TestPassword123!')
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_todas_las_areas_excluye_pc_genericos_y_coincide_con_filtros(self):
        all_assets = []
        for rank in range(1, 7):
            department = Departamento.objects.create(nombre=f'Área QA {rank}')
            person = Usuario.objects.create(
                nombre_completo=f'Persona Top {rank}',
                usuario_red=f'top.qa.{rank}',
                correo_corp=f'top.qa.{rank}@example.com',
                departamento=department,
            )
            for index in range(rank):
                all_assets.append(Equipamiento.objects.create(
                    usuario=person, tipo='Monitor', marca='Dell', modelo='P24',
                    numero_serie=f'QA-TOP-{rank}-{index}', estado='ASIGNADO',
                ))
            if rank == 6:
                PCGenerico.objects.create(
                    usuario_local='pc-top-qa', hostname='PC-TOP-QA',
                    departamento=department,
                )
        unassigned = Equipamiento.objects.create(
            tipo='Celular', marca='Samsung', modelo='A1', estado='STOCK',
        )
        Departamento.objects.create(nombre='Área QA sin equipos')

        response = self.client.get('/api/activos/resumen/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['conteos']['total'], len(all_assets) + 1)
        self.assertEqual(response.data['conteos']['asignados'], len(all_assets))
        self.assertEqual(response.data['conteos']['sin_custodio'], 1)
        self.assertEqual(
            [row['nombre'] for row in response.data['departamentos']],
            [f'Área QA {rank}' for rank in range(6, 0, -1)] + ['Área QA sin equipos'],
        )
        for row in response.data['departamentos']:
            listing = self.client.get('/api/equipos/', {'departamento_id': row['id']})
            self.assertEqual(listing.status_code, 200)
            self.assertEqual(listing.data['count'], row['total'])
        pending = self.client.get('/api/equipos/', {'pendiente': 'sin_custodio'})
        self.assertEqual(pending.data['count'], 1)
        self.assertEqual(pending.data['results'][0]['id'], unassigned.pk)

    def test_qr_inexistente_e_invalido_no_exponen_ficha(self):
        missing = self.client.get(f'/api/activos/qr/{uuid4()}/')
        invalid = self.client.get('/api/activos/qr/no-es-un-uuid/')
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(invalid.status_code, 404)
