from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken


class RefreshTokenSanitizationCommandTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='token-cleanup-test',
            password='StrongPass!123',
        )
        self.token = RefreshToken.for_user(self.user)

    def test_default_is_dry_run(self):
        output = StringIO()
        call_command('sanear_tokens_refresh', stdout=output)
        stored = OutstandingToken.objects.get(jti=self.token['jti'])
        self.assertTrue(stored.token.startswith('eyJ'))
        self.assertIn('Simulación: 1 token(s)', output.getvalue())

    def test_apply_redacts_without_breaking_blacklist(self):
        output = StringIO()
        call_command('sanear_tokens_refresh', apply=True, stdout=output)
        stored = OutstandingToken.objects.get(jti=self.token['jti'])
        self.assertEqual(stored.token, f'redacted:jti:{self.token["jti"]}')
        self.token.blacklist()
        self.assertTrue(hasattr(stored, 'blacklistedtoken'))
        self.assertIn('1 token(s) sanitizados', output.getvalue())
