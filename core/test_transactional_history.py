from datetime import date

from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase

from core.models import (
    Anexo,
    Departamento,
    Equipamiento,
    HistorialAnexo,
    HistorialEquipo,
    HistorialPCGenerico,
    HistorialUsuario,
    PCGenerico,
    Usuario,
)


class HistoryRollbackTests(TransactionTestCase):
    def setUp(self):
        self.department = Departamento.objects.create(
            nombre='Auditoria Transaccional'
        )

    def create_user(self, suffix):
        return Usuario.objects.create(
            nombre_completo=f'Usuario {suffix}',
            usuario_red=f'usuario.{suffix}',
            correo_corp=f'{suffix}@example.com',
            departamento=self.department,
        )

    def test_usuario_history_rolls_back_when_update_fails(self):
        first = self.create_user('primero')
        second = self.create_user('segundo')
        history_count = HistorialUsuario.objects.filter(usuario=first).count()

        first.usuario_red = second.usuario_red.upper()

        with self.assertRaises(IntegrityError):
            first.save()

        self.assertEqual(
            HistorialUsuario.objects.filter(usuario=first).count(),
            history_count,
        )
        first.refresh_from_db()
        self.assertEqual(first.usuario_red, 'usuario.primero')

    def test_anexo_history_rolls_back_when_update_fails(self):
        first = Anexo.objects.create(numero_anexo='8101')
        second = Anexo.objects.create(numero_anexo='8102')
        history_count = HistorialAnexo.objects.filter(anexo=first).count()

        first.numero_anexo = second.numero_anexo

        with self.assertRaises(IntegrityError):
            first.save()

        self.assertEqual(
            HistorialAnexo.objects.filter(anexo=first).count(),
            history_count,
        )
        first.refresh_from_db()
        self.assertEqual(first.numero_anexo, '8101')

    def test_equipment_history_rolls_back_when_update_fails(self):
        first = Equipamiento.objects.create(
            tipo='Celular',
            marca='Marca',
            modelo='Modelo 1',
            numero_serie='SERIE-HIST-1',
            estado='STOCK',
        )
        second = Equipamiento.objects.create(
            tipo='Celular',
            marca='Marca',
            modelo='Modelo 2',
            numero_serie='SERIE-HIST-2',
            estado='STOCK',
        )
        history_count = HistorialEquipo.objects.filter(equipo=first).count()

        first.numero_serie = second.numero_serie.lower()

        with self.assertRaises(IntegrityError):
            first.save()

        self.assertEqual(
            HistorialEquipo.objects.filter(equipo=first).count(),
            history_count,
        )
        first.refresh_from_db()
        self.assertEqual(first.numero_serie, 'SERIE-HIST-1')

    def test_generic_pc_history_rolls_back_when_update_fails(self):
        first = PCGenerico.objects.create(
            usuario_local='pc.local.1',
            hostname='pc-hist-1',
            departamento=self.department,
        )
        second = PCGenerico.objects.create(
            usuario_local='pc.local.2',
            hostname='pc-hist-2',
            departamento=self.department,
        )
        history_count = HistorialPCGenerico.objects.filter(pc=first).count()

        first.hostname = second.hostname.upper()

        with self.assertRaises(IntegrityError):
            first.save()

        self.assertEqual(
            HistorialPCGenerico.objects.filter(pc=first).count(),
            history_count,
        )
        first.refresh_from_db()
        self.assertEqual(first.hostname, 'pc-hist-1')


class AutomaticEquipmentHistoryTests(TestCase):
    def setUp(self):
        self.department = Departamento.objects.create(
            nombre='Sincronizacion Historial'
        )

    def create_user(self, suffix, **overrides):
        values = {
            'nombre_completo': f'Usuario {suffix}',
            'usuario_red': f'usuario.{suffix}',
            'correo_corp': f'{suffix}@example.com',
            'departamento': self.department,
        }
        values.update(overrides)
        return Usuario.objects.create(**values)

    def test_user_deactivation_releases_equipment_with_history(self):
        user = self.create_user('baja', hostname='host-baja')
        equipment = Equipamiento.objects.create(
            usuario=user,
            tipo='Notebook',
            marca='HP',
            modelo='840',
            numero_serie='SERIE-BAJA-HIST',
            fecha_asignacion=date(2026, 9, 1),
            estado='ASIGNADO',
        )

        user.estado = 'BAJA'
        user.save(update_fields=['estado'])

        equipment.refresh_from_db()
        self.assertIsNone(equipment.usuario)
        self.assertEqual(equipment.estado, 'STOCK')
        self.assertIsNone(equipment.fecha_asignacion)
        history = HistorialEquipo.objects.get(equipo=equipment)
        self.assertIn('Usuario Asignado', history.observacion)
        self.assertEqual(history.usuario_anterior, user.nombre_completo)
        self.assertEqual(history.usuario_nuevo, 'Sin asignar')

    def test_hostname_auto_link_assigns_equipment_with_history(self):
        equipment = Equipamiento.objects.create(
            tipo='Notebook',
            marca='Lenovo',
            modelo='T14',
            numero_serie='SERIE-AUTO-HIST',
            hostname='host-auto-hist',
            estado='STOCK',
        )

        user = self.create_user('automatico', hostname='HOST-AUTO-HIST')

        equipment.refresh_from_db()
        self.assertEqual(equipment.usuario, user)
        self.assertEqual(equipment.estado, 'ASIGNADO')
        history = HistorialEquipo.objects.get(equipo=equipment)
        self.assertIn('Usuario Asignado', history.observacion)
        self.assertEqual(history.usuario_anterior, 'Sin asignar')
        self.assertEqual(history.usuario_nuevo, user.nombre_completo)
