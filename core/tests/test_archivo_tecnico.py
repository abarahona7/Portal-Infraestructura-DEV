import json
import os
import tempfile
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Anexo, Departamento, Equipamiento, IP, PapeleraEvento, Usuario


class ArchivoTecnicoTests(TestCase):
    def setUp(self):
        self.technical = User.objects.create_superuser('tecnico', password='StrongPass!123')
        self.admin = User.objects.create_user('admin-portal', password='StrongPass!123')
        self.admin.groups.add(Group.objects.get_or_create(name='Administrador')[0])
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.department = Departamento.objects.create(nombre='Tecnología')
        self.person = Usuario.objects.create(
            nombre_completo='Persona Prueba', usuario_red='persona.prueba',
            correo_corp='persona@example.com', departamento=self.department,
        )

    def command(self, action, module=None, record_id=None, **options):
        output = StringIO()
        args = [action]
        if module:
            args.append(module)
        if record_id:
            args.append(str(record_id))
        call_command('gestionar_archivo', *args, actor='tecnico', stdout=output, **options)
        return output.getvalue()

    def inspect(self, module, record_id):
        return json.loads(self.command('inspeccionar', module, record_id))

    def archive(self, module, record_id, fingerprint):
        return self.command(
            'archivar', module, record_id, motivo='Solicitud TI-123',
            huella=fingerprint, confirmar=f'ARCHIVAR:{module}:{record_id}',
        )

    def test_portal_cannot_archive_or_restore_even_as_admin_or_superuser(self):
        for account in (self.admin, self.technical):
            self.client.force_authenticate(account)
            self.assertEqual(self.client.delete(f'/api/usuarios/{self.person.pk}/').status_code, 403)
            self.assertEqual(self.client.get('/api/papelera/').status_code, 404)
            self.assertEqual(self.client.post(
                f'/api/papelera/usuarios/{self.person.pk}/restaurar/'
            ).status_code, 404)
        self.assertTrue(Usuario.objects.filter(pk=self.person.pk).exists())

    def test_preview_changes_block_archive_and_preserve_assignments(self):
        preview = self.inspect('usuarios', self.person.pk)
        equipment = Equipamiento.objects.create(
            usuario=self.person, tipo='Notebook', marca='Lenovo', modelo='T14',
            numero_serie='ARCHIVO-STALE-1',
        )
        with self.assertRaises(CommandError):
            self.archive('usuarios', self.person.pk, preview['huella'])
        equipment.refresh_from_db()
        self.assertEqual(equipment.usuario_id, self.person.pk)
        self.assertTrue(Usuario.objects.filter(pk=self.person.pk).exists())
        self.assertFalse(PapeleraEvento.objects.exists())

    def test_archive_keeps_full_relation_snapshot_and_restore_never_reassigns(self):
        equipment = Equipamiento.objects.create(
            usuario=self.person, tipo='Notebook', marca='Lenovo', modelo='T14',
            numero_serie='ARCHIVO-REL-1',
        )
        ip = IP.objects.create(direccion_ip='172.24.1.211', usuario=self.person)
        anexo = Anexo.objects.create(numero_anexo='5311', usuario=self.person)
        preview = self.inspect('usuarios', self.person.pk)
        self.assertEqual(preview['impacto']['equipos'][0]['id'], equipment.pk)
        self.assertEqual(preview['impacto']['ips'][0]['id'], ip.pk)
        self.assertEqual(preview['impacto']['anexos'][0]['id'], anexo.pk)
        self.archive('usuarios', self.person.pk, preview['huella'])
        archived = Usuario.all_objects.get(pk=self.person.pk)
        self.assertIsNotNone(archived.deleted_at)
        event = PapeleraEvento.objects.get(modulo='usuarios', registro_id=self.person.pk,
                                           accion='ARCHIVO')
        self.assertEqual(event.contexto['impacto'], preview['impacto'])
        self.assertIn('TI-123', event.detalle)
        equipment.refresh_from_db()
        ip.refresh_from_db()
        anexo.refresh_from_db()
        self.assertIsNone(equipment.usuario_id)
        self.assertIsNone(ip.usuario_id)
        self.assertIsNone(anexo.usuario_id)

        self.command('restaurar', 'usuarios', self.person.pk,
                     motivo='Solicitud TI-124',
                     confirmar=f'RESTAURAR:usuarios:{self.person.pk}')
        self.assertTrue(Usuario.objects.filter(pk=self.person.pk).exists())
        equipment.refresh_from_db()
        self.assertIsNone(equipment.usuario_id)
        restored_event = PapeleraEvento.objects.get(modulo='usuarios',
                                                   registro_id=self.person.pk,
                                                   accion='RESTAURACION')
        self.assertEqual(restored_event.contexto['impacto'], preview['impacto'])

    def test_department_with_active_users_cannot_be_archived(self):
        preview = self.inspect('departamentos', self.department.pk)
        self.assertEqual(preview['impacto']['usuarios'][0]['id'], self.person.pk)
        with self.assertRaises(CommandError):
            self.archive('departamentos', self.department.pk, preview['huella'])
        self.assertTrue(Departamento.objects.filter(pk=self.department.pk).exists())

    def test_report_contains_archived_and_restored_events_with_private_file(self):
        preview = self.inspect('usuarios', self.person.pk)
        self.archive('usuarios', self.person.pk, preview['huella'])
        self.command('restaurar', 'usuarios', self.person.pk,
                     motivo='Solicitud TI-124',
                     confirmar=f'RESTAURAR:usuarios:{self.person.pk}')
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'archivo.json')
            self.command('reporte', 'usuarios', salida=path)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            with open(path, encoding='utf-8') as report:
                data = json.load(report)
            self.assertEqual(data['archivados'], [])
            self.assertEqual([event['accion'] for event in data['eventos']],
                             ['ARCHIVO', 'RESTAURACION'])
            self.assertEqual(data['eventos'][0]['contexto']['impacto']['id'], self.person.pk)
            with self.assertRaises(CommandError):
                self.command('reporte', 'usuarios', salida=path)

    def test_command_requires_technical_superuser_and_reason(self):
        with self.assertRaises(CommandError):
            call_command('gestionar_archivo', 'inspeccionar', 'usuarios', self.person.pk,
                         actor='admin-portal', stdout=StringIO())
        preview = self.inspect('usuarios', self.person.pk)
        with self.assertRaises(CommandError):
            self.command('archivar', 'usuarios', self.person.pk,
                         huella=preview['huella'],
                         confirmar=f'ARCHIVAR:usuarios:{self.person.pk}')
        self.assertTrue(Usuario.objects.filter(pk=self.person.pk).exists())
