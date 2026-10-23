"""Contratos A07 de límites, revocación y autenticación en tiempo real."""

from copy import deepcopy

from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from config.asgi import application
from core.client_ip import get_client_ip_from_meta
from core.models import Equipamiento, PortalSession, SecurityAuditLog


User = get_user_model()


def throttle_settings(**rates):
    config = deepcopy(settings.REST_FRAMEWORK)
    config['DEFAULT_THROTTLE_RATES'].update(rates)
    return override_settings(REST_FRAMEWORK=config)


class AuthenticationRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_login_limita_por_usuario_aunque_cambie_la_ip(self):
        with throttle_settings(login_ip='100/min', login_username='2/15min'):
            responses = [
                APIClient().post(
                    '/api/auth/login/',
                    {'username': 'cuenta-objetivo', 'password': 'incorrecta'},
                    format='json',
                    REMOTE_ADDR=f'198.51.100.{index}',
                )
                for index in range(1, 4)
            ]
        self.assertEqual([response.status_code for response in responses], [401, 401, 429])
        self.assertEqual(
            responses[-1].data['detail'],
            'Demasiadas solicitudes. Intenta nuevamente más tarde.',
        )
        self.assertIn('Retry-After', responses[-1])
        self.assertTrue(SecurityAuditLog.objects.filter(event='RATE_LIMITED').exists())

    def test_login_limita_por_ip_aunque_cambie_el_usuario(self):
        with throttle_settings(login_ip='2/min', login_username='100/15min'):
            responses = [
                APIClient().post(
                    '/api/auth/login/',
                    {'username': f'cuenta-{index}', 'password': 'incorrecta'},
                    format='json',
                    REMOTE_ADDR='198.51.100.40',
                )
                for index in range(1, 4)
            ]
        self.assertEqual([response.status_code for response in responses], [401, 401, 429])

    def test_refresh_tiene_limite_independiente(self):
        with throttle_settings(refresh='1/min'):
            first = self.client.post('/api/auth/refresh/')
            second = self.client.post('/api/auth/refresh/')
        self.assertEqual(first.status_code, 401)
        self.assertEqual(second.status_code, 429)

    def test_api_general_limita_por_usuario(self):
        group, _ = Group.objects.get_or_create(name='Administrador')
        user = User.objects.create_user('rate-user', password='StrongPass!123')
        user.groups.add(group)
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        with throttle_settings(api_user='1/min'):
            first = api_client.get('/api/reference-data/')
            second = api_client.get('/api/reference-data/')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)

    def test_operacion_pesada_tiene_limite_independiente(self):
        group, _ = Group.objects.get_or_create(name='Administrador')
        user = User.objects.create_user('heavy-user', password='StrongPass!123')
        user.groups.add(group)
        equipment = Equipamiento.objects.create(
            tipo='Notebook', marca='QA', modelo='Carga', estado='STOCK',
        )
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        path = f'/api/activos/qr/{equipment.token_qr}/imagen/'
        with throttle_settings(heavy='1/hour'):
            first = api_client.get(path)
            second = api_client.get(path)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)

    def test_admin_login_tiene_limite_por_usuario(self):
        with throttle_settings(
            admin_login_ip='100/min',
            admin_login_username='2/15min',
        ):
            responses = [
                self.client.post(
                    '/admin/login/',
                    {'username': 'admin-objetivo', 'password': 'incorrecta'},
                    REMOTE_ADDR=f'198.51.100.{index}',
                )
                for index in range(1, 4)
            ]
        self.assertEqual([response.status_code for response in responses], [200, 200, 429])
        self.assertIn('Retry-After', responses[-1])


class SessionSecurityChangeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.group, _ = Group.objects.get_or_create(name='Administrador')
        self.user = User.objects.create_user('session-owner', password='StrongPass!123')
        self.user.groups.add(self.group)
        self.client = APIClient()

    def login(self):
        response = self.client.post(
            '/api/auth/login/',
            {'username': self.user.username, 'password': 'StrongPass!123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        return response.data['access']

    def assert_session_revoked(self, access):
        session_id = AccessToken(access)['sid']
        self.assertIsNotNone(PortalSession.objects.get(pk=session_id).revoked_at)
        self.assertEqual(
            self.client.get('/api/auth/me/', HTTP_AUTHORIZATION=f'Bearer {access}').status_code,
            401,
        )

    def test_cambiar_contrasena_revoca_sesiones_y_refresh(self):
        access = self.login()
        self.user.set_password('DifferentPass!456')
        self.user.save(update_fields=['password'])
        self.assert_session_revoked(access)
        self.assertEqual(
            BlacklistedToken.objects.filter(token__user=self.user).count(),
            OutstandingToken.objects.filter(user=self.user).count(),
        )

    def test_desactivar_usuario_revoca_sesiones(self):
        access = self.login()
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assert_session_revoked(access)

    def test_cambiar_rol_revoca_sesiones(self):
        access = self.login()
        self.user.groups.clear()
        self.assert_session_revoked(access)

    def test_refresh_anterior_no_se_puede_reutilizar(self):
        self.login()
        old_refresh = self.client.cookies[settings.JWT_REFRESH_COOKIE].value
        self.assertEqual(self.client.post('/api/auth/refresh/').status_code, 200)
        self.client.cookies[settings.JWT_REFRESH_COOKIE] = old_refresh
        self.assertEqual(self.client.post('/api/auth/refresh/').status_code, 401)

    def test_login_no_persiste_refresh_reutilizable(self):
        self.login()
        raw_refresh = self.client.cookies[settings.JWT_REFRESH_COOKIE].value
        token = RefreshToken(raw_refresh)
        stored = OutstandingToken.objects.get(jti=token['jti'])
        self.assertEqual(stored.token, f'redacted:jti:{token["jti"]}')
        self.assertNotIn(raw_refresh, stored.token)

    def test_rotacion_no_persiste_nuevo_refresh_reutilizable(self):
        self.login()
        self.assertEqual(self.client.post('/api/auth/refresh/').status_code, 200)
        raw_refresh = self.client.cookies[settings.JWT_REFRESH_COOKIE].value
        token = RefreshToken(raw_refresh)
        stored = OutstandingToken.objects.get(jti=token['jti'])
        self.assertEqual(stored.token, f'redacted:jti:{token["jti"]}')

    def test_contrasena_actual_no_se_puede_reutilizar(self):
        with self.assertRaises(ValidationError):
            validate_password('StrongPass!123', self.user)
        self.assertIn('old_password', PasswordChangeForm.base_fields)


class TrustedProxyTests(SimpleTestCase):
    def test_jwt_declara_algoritmo_y_clave_independiente(self):
        self.assertEqual(jwt_settings.ALGORITHM, 'HS256')
        self.assertNotEqual(jwt_settings.SIGNING_KEY, settings.SECRET_KEY)
        self.assertNotEqual(jwt_settings.SIGNING_KEY, settings.FIELD_ENCRYPTION_KEY)

    @override_settings(PORTAL_TRUSTED_PROXY_IPS=['127.0.0.1'])
    def test_x_forwarded_for_solo_se_acepta_desde_proxy_confiable(self):
        self.assertEqual(get_client_ip_from_meta({
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_X_FORWARDED_FOR': '203.0.113.8',
        }), '203.0.113.8')
        self.assertEqual(get_client_ip_from_meta({
            'REMOTE_ADDR': '198.51.100.9',
            'HTTP_X_FORWARDED_FOR': '203.0.113.8',
        }), '198.51.100.9')


class WebSocketAuthenticationTests(SimpleTestCase):
    async def asyncSetUp(self):
        await sync_to_async(cache.clear)()

    async def asyncTearDown(self):
        await sync_to_async(cache.clear)()

    async def test_token_invalido_cierra_websocket(self):
        communicator = WebsocketCommunicator(
            application,
            '/ws/changes/',
            headers=[(b'origin', b'http://localhost:5178')],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.send_json_to({'type': 'auth', 'token': 'token-invalido'})
        output = await communicator.receive_output(timeout=1)
        self.assertEqual(output, {'type': 'websocket.close', 'code': 4401})

    @override_settings(PORTAL_WS_MAX_MESSAGE_BYTES=32)
    async def test_mensaje_demasiado_grande_cierra_websocket(self):
        communicator = WebsocketCommunicator(
            application,
            '/ws/changes/',
            headers=[(b'origin', b'http://localhost:5178')],
        )
        self.assertTrue((await communicator.connect())[0])
        await communicator.send_to(text_data='{"type":"auth","token":"' + ('x' * 40) + '"}')
        self.assertEqual(
            await communicator.receive_output(timeout=1),
            {'type': 'websocket.close', 'code': 4400},
        )
        await communicator.disconnect()

    async def test_auth_con_campos_inesperados_se_ignora(self):
        communicator = WebsocketCommunicator(
            application,
            '/ws/changes/',
            headers=[(b'origin', b'http://localhost:5178')],
        )
        self.assertTrue((await communicator.connect())[0])
        await communicator.send_json_to({
            'type': 'auth', 'token': 'no-debe-validarse', 'extra': 'rechazado',
        })
        await communicator.send_json_to({'type': 'auth', 'token': 'token-invalido'})
        self.assertEqual(
            await communicator.receive_output(timeout=1),
            {'type': 'websocket.close', 'code': 4401},
        )
        await communicator.disconnect()

    @override_settings(PORTAL_WS_MAX_CONNECTIONS_PER_IP=1)
    async def test_limita_conexiones_por_ip(self):
        first = WebsocketCommunicator(
            application,
            '/ws/changes/',
            headers=[(b'origin', b'http://localhost:5178')],
        )
        second = WebsocketCommunicator(
            application,
            '/ws/changes/',
            headers=[(b'origin', b'http://localhost:5178')],
        )
        self.assertTrue((await first.connect())[0])
        connected, close_code = await second.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4429)
        await first.disconnect()

    @override_settings(PORTAL_WS_MESSAGES_PER_SECOND=1)
    async def test_limita_mensajes_por_ip(self):
        communicator = WebsocketCommunicator(
            application,
            '/ws/changes/',
            headers=[(b'origin', b'http://localhost:5178')],
        )
        self.assertTrue((await communicator.connect())[0])
        await communicator.send_json_to({'type': 'ignorado'})
        await communicator.send_json_to({'type': 'ignorado'})
        output = await communicator.receive_output(timeout=1)
        self.assertEqual(output, {'type': 'websocket.close', 'code': 4429})


class WebSocketSessionRevocationTests(TransactionTestCase):
    reset_sequences = True

    async def test_logout_cierra_websocket_de_inmediato(self):
        def prepare_login():
            cache.clear()
            group, _ = Group.objects.get_or_create(name='Administrador')
            user = User.objects.create_user('ws-session', password='StrongPass!123')
            user.groups.add(group)
            client = APIClient()
            response = client.post(
                '/api/auth/login/',
                {'username': user.username, 'password': 'StrongPass!123'},
                format='json',
            )
            return client, response.data['access']

        client, access = await sync_to_async(prepare_login, thread_sensitive=True)()
        communicator = WebsocketCommunicator(
            application,
            '/ws/changes/',
            headers=[(b'origin', b'http://localhost:5178')],
        )
        self.assertTrue((await communicator.connect())[0])
        await communicator.send_json_to({'type': 'auth', 'token': access})
        self.assertEqual(await communicator.receive_json_from(timeout=2), {'type': 'ready'})

        response = await sync_to_async(client.post, thread_sensitive=True)('/api/auth/logout/')
        self.assertEqual(response.status_code, 204)
        output = await communicator.receive_output(timeout=2)
        self.assertEqual(output, {'type': 'websocket.close', 'code': 4401})
