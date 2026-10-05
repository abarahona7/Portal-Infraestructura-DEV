import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models.signals import post_save, pre_save
from django.test import TestCase

from core.models import (
    Anexo,
    Departamento,
    Equipamiento,
    HistorialUsuario,
    IP,
    Usuario,
)


class RawFixtureSignalTests(TestCase):
    def test_raw_fixture_signals_do_not_apply_business_side_effects(self):
        department = Departamento.objects.create(nombre='Tecnología')
        user = Usuario.objects.create(
            nombre_completo='Usuario Fixture',
            usuario_red='usuario.fixture',
            correo_corp='usuario.fixture@example.com',
            departamento=department,
            hostname='NB-FIXTURE-01',
        )
        ip = IP.objects.create(
            direccion_ip='172.24.1.240',
            usuario=user,
        )
        equipment = Equipamiento.objects.create(
            usuario=user,
            tipo='Notebook',
            marca='Lenovo',
            modelo='T14',
            numero_serie='FIXTURE-001',
            estado='ASIGNADO',
        )
        extension = Anexo.objects.create(
            numero_anexo='7991',
            usuario=user,
        )
        history_count = HistorialUsuario.objects.filter(usuario=user).count()

        user.estado = 'BAJA'
        pre_save.send(
            sender=Usuario,
            instance=user,
            raw=True,
            using='default',
            update_fields=None,
        )
        post_save.send(
            sender=Usuario,
            instance=user,
            raw=True,
            created=False,
            using='default',
            update_fields=None,
        )

        ip.refresh_from_db()
        equipment.refresh_from_db()
        extension.refresh_from_db()
        self.assertEqual(ip.usuario_id, user.pk)
        self.assertEqual(equipment.usuario_id, user.pk)
        self.assertEqual(extension.usuario_id, user.pk)
        self.assertEqual(
            HistorialUsuario.objects.filter(usuario=user).count(),
            history_count,
        )


class DatabaseMigrationAuditCommandTests(TestCase):
    def test_snapshot_can_be_compared_without_exposing_record_values(self):
        department = Departamento.objects.create(nombre='Operaciones')
        Usuario.objects.create(
            nombre_completo='Dato Confidencial Prueba',
            usuario_red='auditoria.db',
            correo_corp='auditoria.db@example.com',
            departamento=department,
        )

        with TemporaryDirectory() as directory:
            snapshot_path = Path(directory) / 'sqlite-audit.json'
            mysql_path = Path(directory) / 'mysql-audit.json'
            call_command(
                'auditar_migracion_db',
                salida=str(snapshot_path),
                verbosity=0,
            )
            call_command(
                'auditar_migracion_db',
                salida=str(mysql_path),
                comparar=str(snapshot_path),
                verbosity=0,
            )

            payload = json.loads(snapshot_path.read_text(encoding='utf-8'))
            serialized = snapshot_path.read_text(encoding='utf-8')
            self.assertEqual(payload['snapshot_version'], 1)
            self.assertIn('core.usuario', payload['models'])
            self.assertNotIn('core.portalsession', payload['models'])
            self.assertNotIn('Dato Confidencial Prueba', serialized)
            self.assertNotIn('auditoria.db@example.com', serialized)

            Departamento.objects.create(nombre='Cambio Posterior')
            with self.assertRaises(CommandError):
                call_command(
                    'auditar_migracion_db',
                    comparar=str(snapshot_path),
                    verbosity=0,
                )
