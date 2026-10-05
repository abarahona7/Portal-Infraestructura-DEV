"""Inyecta datos inconsistentes en la BD temporal y comprueba las 21 alertas."""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase

from core.models import (
    Anexo, AsignacionIP, Departamento, Equipamiento, IP,
    PCGenerico, PerfilGenerico, SubArea, Usuario,
)
from core.services.asignacion_ips import (
    create_pc_generico_with_ip, create_server_with_ip,
)


class QAReglasIntegridadTests(TestCase):
    def setUp(self):
        self.a = Departamento.objects.create(nombre='Área A QA')
        self.b = Departamento.objects.create(nombre='Área B QA')
        self.sub_a = SubArea.objects.create(departamento=self.a, nombre='Subárea A')
        self.sub_b = SubArea.objects.create(departamento=self.b, nombre='Subárea B')
        self.user = Usuario.objects.create(
            nombre_completo='Persona Integridad QA', usuario_red='integridad.qa',
            correo_corp='integridad.qa@example.com', departamento=self.a,
            subarea=self.sub_a,
        )

    def assert_detected(self, *codes):
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command('validar_integridad_portal', stdout=output, verbosity=0)
        for code in codes:
            with self.subTest(code=code):
                self.assertIn(f'[ERROR] {code}:', output.getvalue())

    def test_detecta_subarea_de_otro_departamento_en_tres_entidades(self):
        profile = PerfilGenerico.objects.create(
            usuario='perfil.integridad', departamento=self.a, subarea=self.sub_a,
        )
        pc = PCGenerico.objects.create(
            usuario_local='local', hostname='PC-INTEGRIDAD',
            departamento=self.a, subarea=self.sub_a,
        )
        Usuario.objects.filter(pk=self.user.pk).update(subarea=self.sub_b)
        PerfilGenerico.objects.filter(pk=profile.pk).update(subarea=self.sub_b)
        PCGenerico.objects.filter(pk=pc.pk).update(subarea=self.sub_b)
        self.assert_detected(
            'usuario_subarea_departamento', 'perfil_subarea_departamento',
            'pc_subarea_departamento',
        )

    def test_detecta_estados_invalidos_de_usuario_y_perfil(self):
        profile = PerfilGenerico.objects.create(
            usuario='perfil.estado', departamento=self.a,
        )
        Usuario.objects.filter(pk=self.user.pk).update(estado='DESCONOCIDO')
        PerfilGenerico.objects.filter(pk=profile.pk).update(estado='DESCONOCIDO')
        self.assert_detected('usuario_estado_invalido', 'perfil_estado_invalido')

    def test_detecta_recursos_incompatibles_con_baja_y_licencia(self):
        inactive_ip = IP.objects.create(
            direccion_ip='172.23.1.150', usuario=self.user,
        )
        medical_user = Usuario.objects.create(
            nombre_completo='Persona Licencia Integridad QA',
            usuario_red='integridad.licencia',
            correo_corp='integridad.licencia@example.com', departamento=self.a,
        )
        IP.objects.create(direccion_ip='172.23.1.151', usuario=medical_user)
        equipment = Equipamiento.objects.create(
            usuario=self.user, tipo='Celular', marca='Samsung', modelo='A1',
            numero_serie='QA-INTEGRIDAD-BAJA', estado='ASIGNADO',
        )
        extension = Anexo.objects.create(numero_anexo='8408', usuario=self.user)
        Usuario.objects.filter(pk=self.user.pk).update(estado='BAJA')
        Usuario.objects.filter(pk=medical_user.pk).update(estado='LICENCIA')
        self.assertEqual(inactive_ip.usuario_id, self.user.pk)
        self.assertEqual(equipment.usuario_id, self.user.pk)
        self.assertEqual(extension.usuario_id, self.user.pk)
        self.assert_detected(
            'usuario_baja_con_ip', 'usuario_licencia_con_ip',
            'usuario_baja_con_equipo', 'usuario_baja_con_anexo',
        )

    def test_detecta_incoherencias_que_un_check_normalmente_impide(self):
        if connection.vendor != 'sqlite':
            self.skipTest('MySQL bloquea estas escrituras por CHECK; se inyectan solo en SQLite temporal.')
        extension = Anexo.objects.create(numero_anexo='8409')
        invalid_state = Equipamiento.objects.create(
            tipo='Celular', marca='Apple', modelo='A1',
            numero_serie='QA-INTEGRIDAD-ESTADO', estado='STOCK',
        )
        invalid_assignment = Equipamiento.objects.create(
            tipo='Tablet', marca='Apple', modelo='A2',
            numero_serie='QA-INTEGRIDAD-ASIGNACION', estado='STOCK',
        )
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA ignore_check_constraints = ON')
            try:
                Anexo.objects.filter(pk=extension.pk).update(estado='ASIGNADO')
                Equipamiento.objects.filter(pk=invalid_state.pk).update(estado='DESCONOCIDO')
                Equipamiento.objects.filter(pk=invalid_assignment.pk).update(estado='ASIGNADO')
            finally:
                cursor.execute('PRAGMA ignore_check_constraints = OFF')
        self.assert_detected(
            'equipo_estado_invalido', 'anexo_estado_asignacion',
            'equipo_estado_asignacion',
        )

    def test_detecta_ip_libre_con_asignacion_y_reservada_sin_ella(self):
        free = IP.objects.create(
            direccion_ip='172.23.1.152', asignado_otro='Cámara A QA',
        )
        reserved = IP.objects.create(
            direccion_ip='172.23.1.153', asignado_otro='Cámara B QA',
        )
        IP.objects.filter(pk=free.pk).update(estado='LIBRE', asignado_otro=None)
        AsignacionIP.objects.filter(ip=reserved).delete()
        self.assert_detected('ip_libre_con_asignacion', 'ip_reservada_sin_asignacion')

    def test_detecta_cuatro_proyecciones_desincronizadas(self):
        second_user = Usuario.objects.create(
            nombre_completo='Persona Alterna Integridad QA',
            usuario_red='integridad.alterna',
            correo_corp='integridad.alterna@example.com', departamento=self.a,
        )
        user_ip = IP.objects.create(
            direccion_ip='172.23.1.154', usuario=self.user,
        )
        server_ip = IP.objects.create(direccion_ip='172.23.1.155')
        server = create_server_with_ip(server_ip.pk, {'hostname': 'SRV-INTEGRIDAD-QA'})
        pc_ip = IP.objects.create(direccion_ip='172.23.1.156')
        pc = create_pc_generico_with_ip(
            pc_ip.direccion_ip,
            {'usuario_local': 'local.qa', 'hostname': 'PC-IP-INTEGRIDAD-QA',
             'departamento': self.a},
        )
        other_ip = IP.objects.create(
            direccion_ip='172.23.1.157', asignado_otro='Cámara anterior QA',
        )

        IP.objects.filter(pk=user_ip.pk).update(usuario=second_user)
        type(server).objects.filter(pk=server.pk).update(ip=None)
        PCGenerico.objects.filter(pk=pc.pk).update(ip=None)
        IP.objects.filter(pk=other_ip.pk).update(asignado_otro='Cámara distinta QA')
        self.assert_detected(
            'ip_usuario_desincronizada', 'ip_servidor_desincronizada',
            'ip_pc_desincronizada', 'ip_otro_desincronizada',
        )

    def test_detecta_proyecciones_sin_asignacion_central(self):
        user_ip = IP.objects.create(
            direccion_ip='172.23.1.158', usuario=self.user,
        )
        server_ip = IP.objects.create(direccion_ip='172.23.1.159')
        server = create_server_with_ip(server_ip.pk, {'hostname': 'SRV-SIN-CENTRAL-QA'})
        pc_ip = IP.objects.create(direccion_ip='172.23.1.160')
        pc = create_pc_generico_with_ip(
            pc_ip.direccion_ip,
            {'usuario_local': 'local.qa', 'hostname': 'PC-SIN-CENTRAL-QA',
             'departamento': self.a},
        )
        for ip in (user_ip, server_ip, pc_ip):
            AsignacionIP.objects.filter(ip=ip).delete()
        self.assertTrue(type(server).objects.filter(pk=server.pk, ip=server_ip).exists())
        self.assertTrue(PCGenerico.objects.filter(pk=pc.pk, ip=pc_ip).exists())
        self.assert_detected(
            'usuario_ip_sin_asignacion_central',
            'servidor_ip_sin_asignacion_central',
            'pc_ip_sin_asignacion_central',
        )
