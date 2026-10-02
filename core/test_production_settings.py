"""El perfil productivo debe impedir etiquetas QR con una URL inutilizable."""

import os
import secrets
import subprocess
import sys

from cryptography.fernet import Fernet
from django.test import SimpleTestCase


class ProductionQrUrlSettingsTests(SimpleTestCase):
    def check_production(self, public_url):
        environment = os.environ.copy()
        environment.update({
            'DJANGO_ENV': 'production',
            'DJANGO_DEBUG': 'False',
            'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
            'DJANGO_ALLOWED_HOSTS': 'portal.example.cl',
            'FIELD_ENCRYPTION_KEY': Fernet.generate_key().decode(),
            'DATABASE_ENGINE': 'mysql',
            'DATABASE_NAME': 'example',
            'DATABASE_USER': 'example',
            'DATABASE_PASSWORD': 'example',
            'DATABASE_HOST': '127.0.0.1',
            'PORTAL_PUBLIC_URL': public_url,
            'CORS_ALLOWED_ORIGINS': 'https://portal.example.cl',
            'CSRF_TRUSTED_ORIGINS': 'https://portal.example.cl',
            'JWT_COOKIE_SECURE': 'True',
            'SESSION_COOKIE_SECURE': 'True',
            'CSRF_COOKIE_SECURE': 'True',
            'SECURE_SSL_REDIRECT': 'True',
            'SECURE_HSTS_SECONDS': '31536000',
            'SECURE_HSTS_INCLUDE_SUBDOMAINS': 'True',
        })
        return subprocess.run(
            [sys.executable, 'manage.py', 'check', '--deploy', '--settings=config.settings_production'],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_https_url_allows_production_checks(self):
        result = self.check_production('https://portal.example.cl')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_http_url_blocks_production_startup(self):
        result = self.check_production('http://portal.example.cl')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PORTAL_PUBLIC_URL', result.stderr)
