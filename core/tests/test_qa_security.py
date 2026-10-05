"""Seguridad de secretos, sesiones y trazabilidad con datos sintéticos."""

from io import StringIO
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken

from core.models import (
    Departamento,
    Equipamiento,
    PCGenerico,
    PerfilGenerico,
    PortalSession,
    SecurityAuditLog,
    Usuario,
)
from core.security_views import RevealSecretView


@override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
class QASecretosTests(TestCase):
    def setUp(self):
        cache.clear()
        group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user('qa-secrets', password='TestPassword123!')
        self.admin.groups.add(group)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        department = Departamento.objects.create(nombre='Seguridad QA')
        self.person = Usuario.objects.create(
            nombre_completo='Persona Seguridad QA', usuario_red='seguridad.qa',
            correo_corp='seguridad.qa@example.com', departamento=department,
            password_gmail='gmail-qa-secreto', password_vpn='vpn-qa-secreto',
        )
        self.equipment = Equipamiento.objects.create(
            tipo='Celular', marca='Apple', modelo='iPhone',
            numero_serie='QA-SECRET-CEL', estado='STOCK',
            pin='pin-qa-secreto', icloud_password='icloud-qa-secreto',
        )
        self.profile = PerfilGenerico.objects.create(
            usuario='perfil.qa', departamento=department,
            password='perfil-qa-secreto',
        )
        self.pc = PCGenerico.objects.create(
            usuario_local='local.qa', hostname='PC-SECRET-QA',
            departamento=department, password='pc-qa-secreto',
        )

    def secret_cases(self):
        return (
            ('usuario', self.person, 'password_gmail', 'gmail-qa-secreto', '/api/usuarios/'),
            ('usuario', self.person, 'password_vpn', 'vpn-qa-secreto', '/api/usuarios/'),
            ('equipamiento', self.equipment, 'pin', 'pin-qa-secreto', '/api/equipos/'),
            ('equipamiento', self.equipment, 'icloud_password', 'icloud-qa-secreto', '/api/equipos/'),
            ('perfil-generico', self.profile, 'password', 'perfil-qa-secreto', '/api/perfiles-genericos/'),
            ('pc-generico', self.pc, 'password', 'pc-qa-secreto', '/api/pcs-genericos/'),
        )

    @patch.object(RevealSecretView, 'throttle_classes', [])
    def test_seis_secretos_cifrados_ocultos_en_listados_y_revelados_con_auditoria(self):
        for module, obj, field, plain, list_path in self.secret_cases():
            with self.subTest(module=module, field=field):
                obj.refresh_from_db()
                self.assertTrue(getattr(obj, field).startswith('ENC2::'))
                self.assertNotIn(plain, str(self.client.get(list_path).data))
                response = self.client.post(
                    '/api/secrets/reveal/',
                    {'module': module, 'object_id': obj.pk,
                     'secret_type': field, 'password': 'TestPassword123!'},
                    format='json',
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['secret'], plain)
                self.assertEqual(response['Cache-Control'], 'no-store, private')
                audit = SecurityAuditLog.objects.filter(
                    event='SECRET_REVEAL', module=module,
                    object_id_text=str(obj.pk), secret_type=field,
                ).latest('pk')
                self.assertTrue(audit.success)
                self.assertEqual(audit.actor, self.admin.username)
                self.assertEqual(audit.request_id, response['X-Request-ID'])
                self.assertNotIn(plain, audit.detail or '')
        self.assertEqual(SecurityAuditLog.objects.filter(
            event='SECRET_REVEAL', success=True,
        ).count(), 6)
        self.assertNotIn('TestPassword123!', self.admin.password)
        self.assertTrue(self.admin.check_password('TestPassword123!'))

    def test_auditoria_de_revelado_conserva_id_de_solicitud_documentado(self):
        response = self.client.post(
            '/api/secrets/reveal/',
            {'module': 'usuario', 'object_id': self.person.pk,
             'secret_type': 'password_gmail', 'password': 'incorrecta'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        audit = SecurityAuditLog.objects.get(event='SECRET_REVEAL', success=False)
        self.assertEqual(audit.actor, self.admin.username)
        self.assertTrue(hasattr(audit, 'request_id'), 'SecurityAuditLog no guarda request_id')
        self.assertEqual(audit.request_id, response['X-Request-ID'])

    def test_verify_secrets_rechaza_clave_fernet_incorrecta(self):
        with override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            with self.assertRaises(CommandError):
                call_command('verify_secrets', stdout=StringIO())

    def test_verify_secrets_descifra_los_seis_campos_con_clave_correcta(self):
        output = StringIO()
        call_command('verify_secrets', stdout=output)
        self.assertIn('6 secretos ENC2:: descifrados', output.getvalue())
        self.assertNotIn('gmail-qa-secreto', output.getvalue())

    def test_verify_secrets_rechaza_clave_ausente_y_token_danado(self):
        with override_settings(FIELD_ENCRYPTION_KEY=''):
            with self.assertRaises(CommandError):
                call_command('verify_secrets', stdout=StringIO())

        Usuario.objects.filter(pk=self.person.pk).update(password_gmail='ENC2::token-invalido')
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command('verify_secrets', stdout=output)
        self.assertIn('Usuario:', output.getvalue())
        self.assertNotIn('token-invalido', output.getvalue())

    def test_revelado_limita_los_intentos_repetidos(self):
        responses = []
        for _ in range(6):
            responses.append(self.client.post(
                '/api/secrets/reveal/',
                {'module': 'usuario', 'object_id': self.person.pk,
                 'secret_type': 'password_gmail', 'password': 'incorrecta'},
                format='json',
            ))
        self.assertTrue(all(response.status_code == 403 for response in responses[:5]))
        self.assertEqual(responses[5].status_code, 429)
        self.assertEqual(SecurityAuditLog.objects.filter(
            event='SECRET_REVEAL', success=False,
        ).count(), 5)


class QASesionRevocacionTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user('qa-session', password='TestPassword123!')
        self.admin.groups.add(group)
        self.client = APIClient()

    def test_logout_revoca_solo_la_sesion_que_sale(self):
        second = APIClient()
        first_login = self.client.post(
            '/api/auth/login/',
            {'username': 'qa-session', 'password': 'TestPassword123!'},
            format='json',
        )
        second_login = second.post(
            '/api/auth/login/',
            {'username': 'qa-session', 'password': 'TestPassword123!'},
            format='json',
        )
        self.assertEqual(first_login.status_code, 200)
        self.assertEqual(second_login.status_code, 200)
        first_access = first_login.data['access']
        second_access = second_login.data['access']
        first_sid = AccessToken(first_access)['sid']
        second_sid = AccessToken(second_access)['sid']

        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 204)
        self.assertIsNotNone(PortalSession.objects.get(pk=first_sid).revoked_at)
        self.assertIsNone(PortalSession.objects.get(pk=second_sid).revoked_at)
        self.assertEqual(self.client.get(
            '/api/usuarios/', HTTP_AUTHORIZATION=f'Bearer {first_access}',
        ).status_code, 401)
        self.assertEqual(second.get(
            '/api/usuarios/', HTTP_AUTHORIZATION=f'Bearer {second_access}',
        ).status_code, 200)

    def test_refresh_reemplaza_cookie_y_bloquea_token_anterior(self):
        login = self.client.post(
            '/api/auth/login/',
            {'username': 'qa-session', 'password': 'TestPassword123!'},
            format='json',
        )
        self.assertEqual(login.status_code, 200)
        old_refresh = self.client.cookies[settings.JWT_REFRESH_COOKIE].value
        before = BlacklistedToken.objects.count()

        refreshed = self.client.post('/api/auth/refresh/')

        self.assertEqual(refreshed.status_code, 200)
        self.assertNotEqual(self.client.cookies[settings.JWT_REFRESH_COOKIE].value, old_refresh)
        self.assertEqual(BlacklistedToken.objects.count(), before + 1)
