"""Regresiones de estado de colaboradores sobre recursos relacionados."""

from unittest.mock import patch

from django.test import TestCase

from core.models import (
    Anexo,
    AsignacionIP,
    Departamento,
    Equipamiento,
    HistorialAnexo,
    HistorialAsignacionIP,
    HistorialEquipo,
    HistorialUsuario,
    IP,
    Usuario,
)


class QAReactivacionUsuarioTests(TestCase):
    def setUp(self):
        self.departamento = Departamento.objects.create(nombre='Tecnología QA')
        self.usuario = Usuario.objects.create(
            nombre_completo='Colaborador QA',
            usuario_red='colaborador.qa',
            correo_corp='colaborador.qa@example.com',
            departamento=self.departamento,
            hostname='NB-QA-01',
        )
        self.notebook = Equipamiento.objects.create(
            usuario=self.usuario,
            tipo='Notebook',
            marca='Lenovo',
            modelo='T14',
            numero_serie='QA-REACT-NB',
            estado='ASIGNADO',
        )
        self.celular = Equipamiento.objects.create(
            usuario=self.usuario,
            tipo='Celular',
            marca='Samsung',
            modelo='A1',
            numero_serie='QA-REACT-CEL',
            estado='ASIGNADO',
        )
        self.ip = IP.objects.create(
            direccion_ip='172.23.1.240', usuario=self.usuario,
        )
        self.anexo = Anexo.objects.create(
            numero_anexo='8401', usuario=self.usuario,
        )

    def test_baja_y_reactivacion_no_restauran_ip_ni_anexo_pero_enlazan_notebook(self):
        self.usuario.estado = 'BAJA'
        self.usuario.save(update_fields=['estado'])
        self.notebook.refresh_from_db()
        self.celular.refresh_from_db()
        self.ip.refresh_from_db()
        self.anexo.refresh_from_db()
        self.assertIsNone(self.notebook.usuario_id)
        self.assertIsNone(self.celular.usuario_id)
        self.assertEqual(self.ip.estado, 'LIBRE')
        self.assertIsNone(self.anexo.usuario_id)

        # Los espacios externos y las mayúsculas no impiden la coincidencia.
        self.usuario.hostname = '  nb-qa-01  '
        self.usuario.estado = 'ACTIVO'
        self.usuario.save(update_fields=['hostname', 'estado'])
        self.notebook.refresh_from_db()
        self.celular.refresh_from_db()
        self.ip.refresh_from_db()
        self.anexo.refresh_from_db()

        self.assertEqual(self.notebook.usuario_id, self.usuario.pk)
        self.assertEqual(self.notebook.estado, 'ASIGNADO')
        self.assertIsNone(self.celular.usuario_id)
        self.assertIsNone(self.ip.usuario_id)
        self.assertEqual(self.ip.estado, 'LIBRE')
        self.assertFalse(AsignacionIP.objects.filter(usuario=self.usuario).exists())
        self.assertIsNone(self.anexo.usuario_id)
        self.assertTrue(HistorialEquipo.objects.filter(
            equipo=self.notebook,
            usuario_anterior='Sin asignar',
            usuario_nuevo=self.usuario.nombre_completo,
        ).exists())
        self.assertTrue(HistorialUsuario.objects.filter(
            usuario=self.usuario,
            accion='ASIGNACION_EQUIPO',
            objeto_relacionado_id=str(self.notebook.pk),
        ).exists())

    def test_reactivacion_sin_hostname_coincidente_no_recupera_equipos(self):
        self.usuario.estado = 'BAJA'
        self.usuario.save(update_fields=['estado'])
        self.usuario.hostname = 'OTRO-HOST'
        self.usuario.estado = 'ACTIVO'
        self.usuario.save(update_fields=['hostname', 'estado'])

        self.notebook.refresh_from_db()
        self.celular.refresh_from_db()
        self.assertIsNone(self.notebook.usuario_id)
        self.assertIsNone(self.celular.usuario_id)

    def test_fallo_al_liberar_anexo_revierte_baja_y_todos_sus_efectos(self):
        counts = {
            'ip': HistorialAsignacionIP.objects.count(),
            'equipo': HistorialEquipo.objects.count(),
            'anexo': HistorialAnexo.objects.count(),
            'usuario': HistorialUsuario.objects.count(),
        }
        self.usuario.estado = 'BAJA'
        with patch.object(Anexo, 'save', side_effect=RuntimeError('fallo QA en anexo')):
            with self.assertRaises(RuntimeError):
                self.usuario.save(update_fields=['estado'])

        for registro in (self.usuario, self.notebook, self.celular, self.ip, self.anexo):
            registro.refresh_from_db()
        self.assertEqual(self.usuario.estado, 'ACTIVO')
        self.assertEqual(self.notebook.usuario_id, self.usuario.pk)
        self.assertEqual(self.celular.usuario_id, self.usuario.pk)
        self.assertEqual(self.ip.usuario_id, self.usuario.pk)
        self.assertTrue(AsignacionIP.objects.filter(usuario=self.usuario, ip=self.ip).exists())
        self.assertEqual(self.anexo.usuario_id, self.usuario.pk)
        self.assertEqual(HistorialAsignacionIP.objects.count(), counts['ip'])
        self.assertEqual(HistorialEquipo.objects.count(), counts['equipo'])
        self.assertEqual(HistorialAnexo.objects.count(), counts['anexo'])
        self.assertEqual(HistorialUsuario.objects.count(), counts['usuario'])
