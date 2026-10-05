"""El perfil productivo debe impedir etiquetas QR con una URL inutilizable."""

import os
import secrets
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from django.test import SimpleTestCase


class ProductionQrUrlSettingsTests(SimpleTestCase):
    def check_production(self, public_url, redis_url='redis://127.0.0.1:6379/1'):
        environment = os.environ.copy()
        environment.update({
            'DJANGO_SETTINGS_MODULE': 'config.settings_production',
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
            'PORTAL_CHANNEL_REDIS_URL': redis_url,
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
            [sys.executable, '-c', 'from django.conf import settings; print(settings.PORTAL_PUBLIC_URL)'],
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_https_url_allows_production_settings_load(self):
        result = self.check_production('https://portal.example.cl')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_http_url_blocks_production_startup(self):
        result = self.check_production('http://portal.example.cl')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PORTAL_PUBLIC_URL', result.stderr)

    def test_production_requires_shared_redis_layer(self):
        result = self.check_production('https://portal.example.cl', redis_url='')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PORTAL_CHANNEL_REDIS_URL', result.stderr)
