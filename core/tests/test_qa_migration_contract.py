"""Contratos de esquema y carga que deben sobrevivir a la reconstrucción."""

import json
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase

from core.models import Departamento, Equipamiento, PortalSession


class QAEsquemaYFixtureTests(TestCase):
    def test_migracion_0058_elimina_itam_pero_conserva_token_qr(self):
        self.assertTrue(MigrationRecorder.Migration.objects.filter(
            app='core', name__startswith='0058',
        ).exists())
        model_names = {model.__name__ for model in apps.get_app_config('core').get_models()}
        tables = set(connection.introspection.table_names())
        for name in ('MovimientoActivo', 'ActaEntrega', 'ActaEstadoEvento', 'FolioContador'):
            with self.subTest(model=name):
                self.assertNotIn(name, model_names)
                self.assertNotIn(f'core_{name.lower()}', tables)
        self.assertIn('token_qr', {field.name for field in Equipamiento._meta.fields})
        self.assertNotIn('rut', {field.name for field in apps.get_model('core', 'Usuario')._meta.fields})

    def test_fixture_documentada_excluye_sesiones_y_conserva_qr(self):
        admin = User.objects.create_user('qa-fixture', password='TestPassword123!')
        PortalSession.objects.create(user=admin)
        asset = Equipamiento.objects.create(
            tipo='Notebook', marca='Dell', modelo='5400',
            numero_serie='QA-FIXTURE-001', estado='STOCK',
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'portal.json'
            call_command(
                'dumpdata',
                natural_foreign=True, natural_primary=True,
                exclude=(
                    'contenttypes', 'auth.permission', 'admin.logentry',
                    'sessions.session', 'token_blacklist', 'core.portalsession',
                ),
                output=str(path), verbosity=0,
            )
            payload = json.loads(path.read_text(encoding='utf-8'))

        models = {row['model'] for row in payload}
        self.assertIn('core.equipamiento', models)
        for excluded in ('core.portalsession', 'auth.permission', 'contenttypes.contenttype'):
            self.assertNotIn(excluded, models)
        equipment_rows = [row for row in payload if row['model'] == 'core.equipamiento']
        self.assertEqual(len(equipment_rows), 1)
        self.assertEqual(equipment_rows[0]['fields']['token_qr'], str(asset.token_qr))

    def test_brecha_6_loaddata_debe_rechazar_base_con_datos_operacionales(self):
        Departamento.objects.create(nombre='Departamento existente QA')
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'departamentos.json'
            call_command('dumpdata', 'core.Departamento', output=str(path), verbosity=0)
            with self.assertRaises(CommandError):
                call_command('loaddata', str(path), verbosity=0)

    def test_loaddata_admite_base_operacional_vacia(self):
        department = Departamento.objects.create(nombre='Departamento de fixture QA')
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'departamentos.json'
            call_command('dumpdata', 'core.Departamento', output=str(path), verbosity=0)
            # La Papelera deja la fila en la base; esta prueba requiere un
            # destino físicamente vacío para verificar el contrato de loaddata.
            Departamento.all_objects.filter(pk=department.pk).delete()
            call_command('loaddata', str(path), verbosity=0)
        self.assertTrue(Departamento.objects.filter(nombre='Departamento de fixture QA').exists())


class QANormalizacionDocumentadaTests(TestCase):
    def test_nombre_normalizado_elimina_acentos_como_indica_modelo_datos(self):
        department = Departamento.objects.create(nombre='Tecnología')
        self.assertEqual(department.nombre_normalizado, 'tecnologia')

    def test_migracion_recalcula_clave_heredada_sin_cambiar_nombre_visible(self):
        department = Departamento.objects.create(nombre='Tecnología')
        Departamento.objects.filter(pk=department.pk).update(nombre_normalizado='tecnología')
        migration = import_module('core.migrations.0059_audit_request_id_accent_normalization')

        migration.rebuild_normalized_keys(apps, SimpleNamespace(connection=connection))

        department.refresh_from_db()
        self.assertEqual(department.nombre, 'Tecnología')
        self.assertEqual(department.nombre_normalizado, 'tecnologia')

    def test_migracion_detiene_colision_antes_de_actualizar_datos(self):
        if connection.vendor != 'sqlite':
            self.skipTest('La colación MySQL ya impide almacenar este par heredado.')
        first = Departamento.objects.create(nombre='Tecnologia')
        Departamento.objects.bulk_create([
            Departamento(nombre='Tecnología', nombre_normalizado='tecnología'),
        ])
        migration = import_module('core.migrations.0059_audit_request_id_accent_normalization')

        with self.assertRaisesRegex(RuntimeError, 'Colisión al normalizar Departamento.nombre'):
            migration.rebuild_normalized_keys(apps, SimpleNamespace(connection=connection))

        first.refresh_from_db()
        self.assertEqual(first.nombre_normalizado, 'tecnologia')
        self.assertTrue(Departamento.objects.filter(nombre_normalizado='tecnología').exists())
