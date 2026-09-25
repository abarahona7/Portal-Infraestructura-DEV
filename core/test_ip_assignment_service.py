from threading import Barrier, Lock, Thread
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase

from core.models import Departamento, IP, Servidor, Usuario
from core.services.asignacion_ips import (
    IpAssignmentError,
    assign_ip_to_user,
    create_server_with_ip,
    update_server_with_ip,
)


class IpAssignmentRollbackTests(TestCase):
    def setUp(self):
        self.department = Departamento.objects.create(nombre='Rollback IP')
        self.user = Usuario.objects.create(
            nombre_completo='Usuario Rollback',
            usuario_red='rollback.ip',
            correo_corp='rollback.ip@example.com',
            departamento=self.department,
        )
        self.first_ip = IP.objects.create(direccion_ip='172.23.1.210')
        self.second_ip = IP.objects.create(direccion_ip='172.23.1.211')

    def test_user_change_rolls_back_when_reservation_fails(self):
        assign_ip_to_user(self.user.pk, self.first_ip.direccion_ip)

        with patch(
            'core.services.asignacion_ips._reserve_user_ip',
            side_effect=RuntimeError('fallo inyectado'),
        ), self.assertRaises(RuntimeError):
            assign_ip_to_user(self.user.pk, self.second_ip.direccion_ip)

        self.first_ip.refresh_from_db()
        self.second_ip.refresh_from_db()
        self.assertEqual(self.first_ip.usuario_id, self.user.pk)
        self.assertEqual(self.first_ip.estado, 'RESERVADA')
        self.assertIsNone(self.second_ip.usuario_id)
        self.assertEqual(self.second_ip.estado, 'LIBRE')

    def test_server_create_rolls_back_when_reservation_fails(self):
        with patch(
            'core.services.asignacion_ips._reserve_server_ip',
            side_effect=RuntimeError('fallo inyectado'),
        ), self.assertRaises(RuntimeError):
            create_server_with_ip(
                self.first_ip.pk,
                {'hostname': 'SRV-ROLLBACK-CREATE'},
            )

        self.first_ip.refresh_from_db()
        self.assertFalse(Servidor.objects.exists())
        self.assertEqual(self.first_ip.estado, 'LIBRE')
        self.assertIsNone(self.first_ip.asignado_otro)

    def test_server_change_rolls_back_when_reservation_fails(self):
        server = create_server_with_ip(
            self.first_ip.pk,
            {'hostname': 'SRV-ROLLBACK-UPDATE'},
        )

        with patch(
            'core.services.asignacion_ips._reserve_server_ip',
            side_effect=RuntimeError('fallo inyectado'),
        ), self.assertRaises(RuntimeError):
            update_server_with_ip(
                server.pk,
                self.second_ip.pk,
                {'descripcion': 'No debe persistir'},
            )

        server.refresh_from_db()
        self.first_ip.refresh_from_db()
        self.second_ip.refresh_from_db()
        self.assertEqual(server.ip_id, self.first_ip.pk)
        self.assertIsNone(server.descripcion)
        self.assertEqual(self.first_ip.estado, 'RESERVADA')
        self.assertEqual(
            self.first_ip.asignado_otro,
            'Servidor: SRV-ROLLBACK-UPDATE',
        )
        self.assertEqual(self.second_ip.estado, 'LIBRE')
        self.assertIsNone(self.second_ip.asignado_otro)


@skipUnless(connection.vendor == 'mysql', 'Requiere bloqueos reales de MySQL.')
class IpAssignmentConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.department = Departamento.objects.create(nombre='Concurrencia IP')
        self.users = [
            Usuario.objects.create(
                nombre_completo=f'Usuario Concurrente {index}',
                usuario_red=f'concurrente{index}',
                correo_corp=f'concurrente{index}@example.com',
                departamento=self.department,
            )
            for index in (1, 2)
        ]
        self.ip = IP.objects.create(direccion_ip='172.23.1.212')

    def test_only_one_user_can_reserve_the_same_ip(self):
        barrier = Barrier(2)
        result_lock = Lock()
        results = []

        def assign(user_id):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                assign_ip_to_user(user_id, self.ip.direccion_ip)
                result = ('ok', user_id)
            except IpAssignmentError:
                result = ('conflict', user_id)
            except Exception as exc:  # pragma: no cover - evidencia del motor real
                result = ('unexpected', type(exc).__name__)
            finally:
                close_old_connections()
            with result_lock:
                results.append(result)

        threads = [Thread(target=assign, args=(user.pk,)) for user in self.users]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual([item[0] for item in results].count('ok'), 1)
        self.assertEqual([item[0] for item in results].count('conflict'), 1)
        self.assertNotIn('unexpected', [item[0] for item in results])

        self.ip.refresh_from_db()
        winner = next(item[1] for item in results if item[0] == 'ok')
        self.assertEqual(self.ip.usuario_id, winner)
        self.assertEqual(self.ip.estado, 'RESERVADA')
