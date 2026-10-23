"""Regresiones A09 para fallos de infraestructura y excepciones internas."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.db import OperationalError
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory

from config.asgi import application
from core.exceptions import portal_exception_handler
from core.models import Departamento, PortalSession, SecurityAuditLog, Usuario
from core.security_events import record_security_event
from core.throttles import LoginIPThrottle


class BrokenCache:
    def get(self, *args, **kwargs):
        raise ConnectionError('cache sintético no disponible')


class ExceptionResponseTests(TestCase):
    def request(self):
        request = APIRequestFactory().get('/api/sintetico/')
        request.request_id = 'request-sintetico-123'
        return request

    def test_excepcion_interna_no_filtra_detalles_y_entrega_correlacion(self):
        response = portal_exception_handler(
            RuntimeError('tabla_secreta valor_secreto'),
            {'request': self.request(), 'view': SimpleNamespace(basename='sintetico')},
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {
            'detail': 'El servicio no pudo completar la operación.',
            'request_id': 'request-sintetico-123',
        })
        self.assertNotIn('tabla_secreta', str(response.data))
        self.assertTrue(SecurityAuditLog.objects.filter(
            event='API_UNHANDLED_EXCEPTION', success=False,
        ).exists())

    def test_error_de_base_responde_503_y_revierte_a_mensaje_generico(self):
        response = portal_exception_handler(
            OperationalError('deadlock sintético'),
            {'request': self.request(), 'view': SimpleNamespace(basename='sintetico')},
        )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn('deadlock', str(response.data))
        self.assertEqual(response.data['request_id'], 'request-sintetico-123')

    def test_cache_caido_deniega_login_con_503_controlado(self):
        with patch.object(LoginIPThrottle, 'cache', BrokenCache()):
            response = self.client.post('/api/auth/login/', {
                'username': 'persona',
                'password': 'secreto-sintetico',
            })

        self.assertEqual(response.status_code, 503)
        self.assertIn('servicio de seguridad', response.json()['detail'].lower())
        self.assertTrue(SecurityAuditLog.objects.filter(
            event='SECURITY_DEPENDENCY_UNAVAILABLE', success=False,
        ).exists())

    def test_umbral_de_login_fallido_emite_alerta_sin_datos_sensibles(self):
        cache.clear()
        with self.assertLogs('portal.security', level='CRITICAL') as captured:
            for _ in range(5):
                record_security_event(
                    event='LOGIN_FAILED', actor='persona-sintetica',
                    module='auth', success=False,
                    detail='CREDENCIALES_INVALIDAS',
                )

        alert = '\n'.join(captured.output)
        self.assertIn('security_alert_threshold_reached', alert)
        self.assertNotIn('secreto-sintetico', alert)


class LogoutFailureTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name='Administrador')
        self.user = User.objects.create_user('logout-failure', password='StrongPass!123')
        self.user.groups.add(group)
        self.client = APIClient()

    def test_logout_con_falla_de_bd_elimina_cookie_y_no_afirma_revocacion(self):
        login = self.client.post('/api/auth/login/', {
            'username': self.user.username,
            'password': 'StrongPass!123',
        }, format='json')
        self.assertEqual(login.status_code, 200)
        session_id = next(iter(PortalSession.objects.filter(user=self.user))).pk

        with patch('core.auth_views.revoke_portal_session', side_effect=OperationalError('caida')):
            response = self.client.post('/api/auth/logout/')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.cookies['siminfra_refresh']['max-age'], 0)
        self.assertIsNone(PortalSession.objects.get(pk=session_id).revoked_at)
        self.assertTrue(SecurityAuditLog.objects.filter(
            event='LOGOUT', success=False,
        ).exists())


class ExportSafetyTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name='Administrador')
        self.user = User.objects.create_user('export-admin', password='StrongPass!123')
        self.user.groups.add(group)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        department = Departamento.objects.create(nombre='Exportacion QA')
        for index in range(2):
            Usuario.objects.create(
                nombre_completo=f'Persona Export {index}',
                usuario_red=f'export{index}',
                correo_corp=f'export{index}@example.com',
                departamento=department,
            )

    def test_exportacion_se_audita_con_cantidad(self):
        response = self.client.get('/api/usuarios/', {'export': '1'})

        self.assertEqual(response.status_code, 200)
        event = SecurityAuditLog.objects.get(event='DATA_EXPORT')
        self.assertEqual(event.actor, self.user.username)
        self.assertEqual(event.detail, 'ROWS:2')

    @override_settings(PORTAL_EXPORT_MAX_ROWS=1)
    def test_exportacion_sobre_limite_se_rechaza_antes_de_entregar_filas(self):
        response = self.client.get('/api/usuarios/', {'export': '1'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('máximo de 1 registros', str(response.data))
        self.assertFalse(SecurityAuditLog.objects.filter(event='DATA_EXPORT').exists())

    def test_exportacion_falla_cerrado_si_no_puede_auditarse(self):
        with patch('core.views.record_security_event', return_value=False):
            response = self.client.get('/api/usuarios/', {'export': '1'})

        self.assertEqual(response.status_code, 503)
        self.assertNotIn('results', response.data)


class WebSocketFailureTests(TransactionTestCase):
    async def test_falla_al_suscribir_grupo_cierra_sin_confirmar_autenticacion(self):
        def login():
            group, _ = Group.objects.get_or_create(name='Administrador')
            user = User.objects.create_user('ws-failure', password='StrongPass!123')
            user.groups.add(group)
            response = APIClient().post('/api/auth/login/', {
                'username': user.username,
                'password': 'StrongPass!123',
            }, format='json')
            return response.data['access']

        access = await sync_to_async(login, thread_sensitive=True)()
        layer = get_channel_layer()
        communicator = WebsocketCommunicator(
            application,
            '/ws/changes/',
            headers=[(b'origin', b'http://localhost:5178')],
        )
        self.assertTrue((await communicator.connect())[0])

        with patch.object(
            layer,
            'group_add',
            new=AsyncMock(side_effect=ConnectionError('channels sintético no disponible')),
        ):
            await communicator.send_json_to({'type': 'auth', 'token': access})
            output = await communicator.receive_output(timeout=2)

        self.assertEqual(output, {'type': 'websocket.close', 'code': 1013})
        await communicator.wait(timeout=2)
