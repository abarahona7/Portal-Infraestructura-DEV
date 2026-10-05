"""Invariante al asignar dos IP simultáneas a un mismo propietario en MySQL 8."""

from threading import Barrier, Lock, Thread
from unittest import skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from core.models import AsignacionIP, Departamento, HistorialAsignacionIP, IP, Usuario
from core.services.asignacion_ips import IpAssignmentError, assign_ip_to_user


@skipUnless(connection.vendor == 'mysql', 'Requiere MySQL 8 aislado con bloqueos reales.')
class QAConcurrenciaMismoPropietarioTests(TransactionTestCase):
    reset_sequences = True

    def test_dos_ips_simultaneas_dejan_una_sola_asignacion_coherente(self):
        department = Departamento.objects.create(nombre='Concurrencia propietario QA')
        user = Usuario.objects.create(
            nombre_completo='Persona Concurrente QA',
            usuario_red='qa.concurrente',
            correo_corp='qa.concurrente@example.com',
            departamento=department,
        )
        ips = [
            IP.objects.create(direccion_ip='172.23.1.241'),
            IP.objects.create(direccion_ip='172.23.1.242'),
        ]
        barrier = Barrier(2)
        lock = Lock()
        results = []

        def assign(address):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                assign_ip_to_user(user.pk, address)
                result = 'ok'
            except IpAssignmentError:
                result = 'conflict'
            except Exception as exc:  # Fallo real del motor, no se oculta como conflicto.
                result = type(exc).__name__
            finally:
                close_old_connections()
            with lock:
                results.append(result)

        threads = [Thread(target=assign, args=(ip.direccion_ip,)) for ip in ips]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item in {'ok', 'conflict'} for item in results), results)
        self.assertIn('ok', results)

        assignments = list(AsignacionIP.objects.filter(usuario=user))
        self.assertEqual(len(assignments), 1)
        chosen = assignments[0].ip
        user.refresh_from_db()
        self.assertEqual(user.ip, chosen)
        self.assertEqual(chosen.usuario_id, user.pk)
        self.assertEqual(chosen.estado, 'RESERVADA')
        for ip in ips:
            ip.refresh_from_db()
            if ip.pk != chosen.pk:
                self.assertEqual(ip.estado, 'LIBRE')
                self.assertIsNone(ip.usuario_id)
                self.assertFalse(AsignacionIP.objects.filter(ip=ip).exists())
        self.assertTrue(HistorialAsignacionIP.objects.filter(
            ip=chosen, accion='ASIGNACION', propietario_id=user.pk,
        ).exists())
