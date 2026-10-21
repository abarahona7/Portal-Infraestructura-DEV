from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError

from core.audit import reset_current_audit_user, set_current_audit_user
from core.models import (
    Anexo, Departamento, Equipamiento, HistorialAsignacionIP, HistorialEquipo, HistorialUsuario,
    IP, PapeleraEvento, Servidor, PCGenerico, Usuario,
)
from core.services.papelera import archive_record, restore_record


class PapeleraYProtocolosTests(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        operator_group, _ = Group.objects.get_or_create(name='Operador Infraestructura')
        self.admin = User.objects.create_user('papelera-admin', password='StrongPass!123')
        self.admin.groups.add(admin_group)
        self.operator = User.objects.create_user('papelera-operador', password='StrongPass!123')
        self.operator.groups.add(operator_group)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.department = Departamento.objects.create(nombre='Tecnología')
        self.user = Usuario.objects.create(
            nombre_completo='Persona de Prueba', usuario_red='persona.prueba',
            correo_corp='persona@example.com', departamento=self.department,
        )

    def archive(self, instance):
        token = set_current_audit_user(self.admin)
        try:
            return archive_record(instance, reason='Solicitud técnica de prueba')
        finally:
            reset_current_audit_user(token)

    def restore(self, module, record_id):
        token = set_current_audit_user(self.admin)
        try:
            return restore_record(module, record_id, reason='Restauración técnica de prueba')
        finally:
            reset_current_audit_user(token)

    def test_status_protocol_is_required_and_logged(self):
        url = f'/api/usuarios/{self.user.pk}/'
        checklist = self.client.get(url).data['protocolos_estado']['BAJA']
        self.assertEqual([item['id'] for item in checklist], ['sin_recursos'])
        self.assertEqual(self.client.patch(url, {'estado': 'BAJA'}, format='json').status_code, 400)
        self.assertEqual(self.user.historial.filter(accion='PROTOCOLO_CONFIRMADO').count(), 0)
        self.assertEqual(self.client.patch(url, {
            'estado': 'BAJA',
            'protocolo_confirmaciones': ['equipos', 'ip', 'anexo'],
        }, format='json').status_code, 400)
        response = self.client.patch(url, {
            'estado': 'BAJA',
            'protocolo_confirmaciones': ['sin_recursos'],
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        event = HistorialUsuario.objects.get(usuario=self.user, accion='PROTOCOLO_CONFIRMADO')
        self.assertEqual(event.modificado_por, self.admin.username)
        self.assertIn('no tiene equipos, IP ni anexo asignados', event.observacion)

    def test_baja_only_confirms_assigned_equipment(self):
        equipment = Equipamiento.objects.create(
            usuario=self.user, tipo='Notebook', marca='Lenovo', modelo='T14',
            numero_serie='PROTO-USER-1',
        )
        url = f'/api/usuarios/{self.user.pk}/'
        checklist = self.client.get(url).data['protocolos_estado']['BAJA']
        self.assertEqual([item['id'] for item in checklist], ['equipos'])
        self.assertEqual(self.client.patch(url, {
            'estado': 'BAJA', 'protocolo_confirmaciones': ['equipos'],
        }, format='json').status_code, 200)
        equipment.refresh_from_db()
        self.assertIsNone(equipment.usuario_id)
        event = HistorialUsuario.objects.get(usuario=self.user, accion='PROTOCOLO_CONFIRMADO')
        self.assertIn('devolución física', event.observacion)
        self.assertNotIn('anexo', event.observacion)

    def test_baja_only_confirms_assigned_extension(self):
        extension = Anexo.objects.create(numero_anexo='5222', usuario=self.user)
        url = f'/api/usuarios/{self.user.pk}/'
        checklist = self.client.get(url).data['protocolos_estado']['BAJA']
        self.assertEqual([item['id'] for item in checklist], ['anexo'])
        self.assertEqual(self.client.patch(url, {
            'estado': 'BAJA', 'protocolo_confirmaciones': ['anexo'],
        }, format='json').status_code, 200)
        extension.refresh_from_db()
        self.assertIsNone(extension.usuario_id)

    def test_protocol_rejects_confirmation_when_assignments_change(self):
        url = f'/api/usuarios/{self.user.pk}/'
        self.assertEqual(
            [item['id'] for item in self.client.get(url).data['protocolos_estado']['BAJA']],
            ['sin_recursos'],
        )
        Anexo.objects.create(numero_anexo='5223', usuario=self.user)
        response = self.client.patch(url, {
            'estado': 'BAJA', 'protocolo_confirmaciones': ['sin_recursos'],
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.estado, 'ACTIVO')

    def test_license_only_confirms_assigned_ip(self):
        ip = IP.objects.create(direccion_ip='172.24.1.211', usuario=self.user)
        url = f'/api/usuarios/{self.user.pk}/'
        checklist = self.client.get(url).data['protocolos_estado']['LICENCIA']
        self.assertEqual([item['id'] for item in checklist], ['ip'])
        self.assertEqual(self.client.patch(url, {
            'estado': 'LICENCIA', 'protocolo_confirmaciones': ['ip'],
        }, format='json').status_code, 200)
        ip.refresh_from_db()
        self.assertIsNone(ip.usuario_id)

    def test_reactivation_requires_protocol_and_never_restores_matching_equipment(self):
        self.user.hostname = 'NB-REACTIVACION-01'
        self.user.save(update_fields=['hostname'])
        equipment = Equipamiento.objects.create(
            usuario=self.user, tipo='Notebook', marca='Lenovo', modelo='T14',
            hostname=self.user.hostname, numero_serie='PROTO-REACT-1',
        )
        url = f'/api/usuarios/{self.user.pk}/'

        self.assertEqual(self.client.patch(url, {
            'estado': 'BAJA', 'protocolo_confirmaciones': ['equipos'],
        }, format='json').status_code, 200)
        equipment.refresh_from_db()
        self.assertIsNone(equipment.usuario_id)
        self.assertEqual(equipment.estado, 'STOCK')

        rejected = self.client.patch(url, {'estado': 'ACTIVO'}, format='json')
        self.assertEqual(rejected.status_code, 400)
        response = self.client.patch(url, {
            'estado': 'ACTIVO', 'protocolo_confirmaciones': ['reactivacion'],
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        equipment.refresh_from_db()
        self.assertIsNone(equipment.usuario_id)
        self.assertEqual(equipment.estado, 'STOCK')
        self.assertTrue(HistorialUsuario.objects.filter(
            usuario=self.user,
            accion='PROTOCOLO_CONFIRMADO',
            observacion__icontains='reactivar',
        ).exists())

    def test_equipment_protocol_is_required_for_assignment_or_status(self):
        equipment = Equipamiento.objects.create(
            tipo='Notebook', marca='Lenovo', modelo='T14', numero_serie='PROTO-1',
        )
        url = f'/api/equipos/{equipment.pk}/'
        self.assertEqual(self.client.patch(url, {'usuario': self.user.pk}, format='json').status_code, 400)
        response = self.client.patch(url, {
            'usuario': self.user.pk,
            'protocolo_confirmaciones': ['custodia', 'identidad', 'estado'],
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['estado'], 'ASIGNADO')
        self.assertTrue(HistorialEquipo.objects.filter(
            equipo=equipment, accion='PROTOCOLO_CONFIRMADO',
            modificado_por=self.admin.username,
        ).exists())

    def test_archiving_user_preserves_record_and_releases_resources(self):
        equipment = Equipamiento.objects.create(
            usuario=self.user, tipo='Notebook', marca='Lenovo', modelo='T14',
            numero_serie='PAPELERA-1',
        )
        ip = IP.objects.create(direccion_ip='172.24.1.211', usuario=self.user)
        anexo = Anexo.objects.create(numero_anexo='5222', usuario=self.user)
        self.archive(self.user)
        self.assertFalse(Usuario.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(Usuario.all_objects.filter(pk=self.user.pk, deleted_at__isnull=False).exists())
        equipment.refresh_from_db()
        ip.refresh_from_db()
        anexo.refresh_from_db()
        self.assertIsNone(equipment.usuario_id)
        self.assertIsNone(ip.usuario_id)
        self.assertIsNone(anexo.usuario_id)
        self.assertTrue(HistorialUsuario.objects.filter(usuario=self.user, accion='ARCHIVO').exists())
        self.assertTrue(PapeleraEvento.objects.filter(modulo='usuarios', registro_id=self.user.pk, accion='ARCHIVO').exists())
        self.assertEqual(self.client.get(f'/api/usuarios/{self.user.pk}/').status_code, 404)

        self.assertEqual(self.client.get('/api/papelera/').status_code, 404)
        self.restore('usuarios', self.user.pk)
        self.assertTrue(Usuario.objects.filter(pk=self.user.pk).exists())
        equipment.refresh_from_db()
        self.assertIsNone(equipment.usuario_id)
        self.assertTrue(HistorialUsuario.objects.filter(usuario=self.user, accion='RESTAURACION').exists())

    def test_archived_equipment_disappears_from_qr_and_dashboard(self):
        equipment = Equipamiento.objects.create(
            tipo='Celular', marca='Apple', modelo='iPhone', numero_serie='PAPELERA-QR',
        )
        token = equipment.token_qr
        self.archive(equipment)
        self.assertEqual(self.client.get(f'/api/activos/qr/{token}/').status_code, 404)
        self.assertFalse(Equipamiento.objects.filter(pk=equipment.pk).exists())
        dashboard = self.client.get('/api/activos/resumen/').json()
        self.assertEqual(dashboard['conteos']['total'], 0)
        self.restore('equipos', equipment.pk)
        equipment.refresh_from_db()
        self.assertEqual(equipment.token_qr, token)

    def test_server_and_pc_release_ip_when_archived(self):
        server_ip = IP.objects.create(direccion_ip='172.23.1.211')
        pc_ip = IP.objects.create(direccion_ip='172.24.1.212')
        server = Servidor.objects.create(hostname='srv-papelera', ip=server_ip)
        pc = PCGenerico.objects.create(
            usuario_local='pc-papelera', hostname='pc-papelera',
            departamento=self.department, ip=pc_ip,
        )
        self.archive(server)
        self.archive(pc)
        server_ip.refresh_from_db()
        pc_ip.refresh_from_db()
        self.assertEqual(server_ip.estado, 'LIBRE')
        self.assertEqual(pc_ip.estado, 'LIBRE')
        self.assertIsNone(Servidor.all_objects.get(pk=server.pk).ip_id)
        self.assertIsNone(PCGenerico.all_objects.get(pk=pc.pk).ip_id)
        self.restore('servidores', server.pk)
        self.assertIsNone(Servidor.objects.get(pk=server.pk).ip_id)

    def test_ip_must_be_free_before_archiving(self):
        ip = IP.objects.create(direccion_ip='172.24.1.213')
        self.assertEqual(self.client.patch(f'/api/usuarios/{self.user.pk}/', {
            'ip_seleccionada': ip.direccion_ip,
        }, format='json').status_code, 200)
        with self.assertRaises(ValidationError):
            self.archive(ip)
        self.assertTrue(IP.objects.filter(pk=ip.pk).exists())
        self.assertEqual(self.client.patch(f'/api/usuarios/{self.user.pk}/', {
            'ip_seleccionada': None,
        }, format='json').status_code, 200)
        self.archive(ip)
        self.assertFalse(IP.objects.filter(pk=ip.pk).exists())
        self.restore('ips', ip.pk)

    def test_archived_unique_identifier_requires_restoration(self):
        equipment = Equipamiento.objects.create(
            tipo='Tablet', marca='Samsung', modelo='A9', numero_serie='UNICO-PAPELERA',
        )
        self.archive(equipment)
        response = self.client.post('/api/equipos/', {
            'tipo': 'Tablet', 'marca': 'Samsung', 'modelo': 'A9',
            'numero_serie': 'UNICO-PAPELERA',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Equipamiento.all_objects.filter(numero_serie='UNICO-PAPELERA').count(), 1)

    def test_creation_and_ip_change_have_history(self):
        equipment = Equipamiento.objects.create(
            tipo='Tablet', marca='Samsung', modelo='A9', numero_serie='HIST-CREACION',
        )
        self.assertTrue(HistorialEquipo.objects.filter(equipo=equipment, accion='CREACION').exists())
        ip = IP.objects.create(direccion_ip='172.24.1.214')
        ip.asignado_otro = 'CCTV'
        ip.save()
        self.assertTrue(HistorialAsignacionIP.objects.filter(ip=ip, accion='REGISTRO').exists())
        self.assertTrue(HistorialAsignacionIP.objects.filter(ip=ip, accion='MODIFICACION').exists())

    def test_equipment_accessories_are_recorded_in_history(self):
        equipment = Equipamiento.objects.create(
            tipo='Notebook', marca='Lenovo', modelo='T14', numero_serie='HIST-ACCESORIOS',
        )
        equipment.accesorios = 'Cargador'
        equipment.save(update_fields=['accesorios'])
        self.assertTrue(HistorialEquipo.objects.filter(
            equipo=equipment, accion='MODIFICACION', observacion__contains='Accesorios:::N/I:::Cargador',
        ).exists())

    def test_parent_must_be_restored_before_archived_user(self):
        self.archive(self.user)
        self.archive(self.department)
        with self.assertRaises(ValidationError):
            self.restore('usuarios', self.user.pk)
        self.restore('departamentos', self.department.pk)
        self.restore('usuarios', self.user.pk)

    def test_orm_delete_also_archives_instead_of_erasing(self):
        self.user.delete()
        self.assertFalse(Usuario.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(Usuario.all_objects.filter(pk=self.user.pk).exists())
        another = Usuario.objects.create(
            nombre_completo='Otra Persona', usuario_red='otra.persona',
            correo_corp='otra@example.com', departamento=self.department,
        )
        Usuario.objects.filter(pk=another.pk).delete()
        self.assertTrue(Usuario.all_objects.filter(pk=another.pk).exists())
