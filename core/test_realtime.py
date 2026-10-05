"""Contratos de notificación y validación de origen del canal."""

from unittest.mock import patch
from urllib.parse import urlparse

from django.test import TestCase

from config.asgi import application
from core.models import Anexo, Equipamiento
from core.realtime import EDITOR_GROUP, VIEWER_GROUP, schedule_change


class RealtimeChangesTests(TestCase):
    def test_notificacion_se_envia_tras_commit_sin_datos_del_equipo(self):
        asset = Equipamiento(pk=42, tipo='Notebook', marca='Dell', modelo='Latitude')
        with patch('core.realtime.get_channel_layer') as layer, \
             patch('core.realtime.async_to_sync') as to_sync:
            with self.captureOnCommitCallbacks(execute=True):
                schedule_change(asset, 'updated')
                self.assertFalse(to_sync.called)
        layer.assert_called_once()
        self.assertEqual(to_sync.call_count, 1)
        args, _ = to_sync.return_value.call_args
        self.assertEqual(args[0], EDITOR_GROUP)
        event = args[1]
        self.assertEqual(event['record_id'], 42)
        self.assertEqual(event['operation'], 'updated')
        self.assertIn('equipos', event['modules'])
        self.assertNotIn('marca', event)

    def test_origen_del_socket_debe_ser_del_portal(self):
        validator = application.application_mapping['websocket']
        self.assertTrue(validator.valid_origin(urlparse('http://localhost:5178')))
        self.assertFalse(validator.valid_origin(urlparse('https://sitio-ajeno.example')))

    def test_visualizador_solo_recibe_cambios_de_anexos(self):
        annex = Anexo(pk=7, numero_anexo='1234')
        with patch('core.realtime.get_channel_layer'), \
             patch('core.realtime.async_to_sync') as to_sync:
            with self.captureOnCommitCallbacks(execute=True):
                schedule_change(annex, 'updated')
        self.assertEqual(to_sync.call_count, 2)
        editor_event = to_sync.return_value.call_args_list[0].args[1]
        viewer_group, viewer_event = to_sync.return_value.call_args_list[1].args
        self.assertEqual(viewer_group, VIEWER_GROUP)
        self.assertIn('usuarios', editor_event['modules'])
        self.assertEqual(viewer_event['modules'], ('anexos',))
