"""El perfil productivo debe impedir etiquetas QR con una URL inutilizable."""

import os
import secrets
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from django.test import SimpleTestCase


class ProductionQrUrlSettingsTests(SimpleTestCase):
    def check_production(
        self,
        public_url,
        redis_url='redis://127.0.0.1:6379/1',
        cache_url='redis://127.0.0.1:6379/2',
        reuse_django_key_for_jwt=False,
        overrides=None,
        unset=(),
    ):
        environment = os.environ.copy()
        django_key = secrets.token_urlsafe(64)
        environment.update({
            'DJANGO_SETTINGS_MODULE': 'config.settings_production',
            'DJANGO_ENV': 'production',
            'DJANGO_DEBUG': 'False',
            'DJANGO_SECRET_KEY': django_key,
            'JWT_SIGNING_KEY': django_key if reuse_django_key_for_jwt else secrets.token_urlsafe(64),
            'DJANGO_ALLOWED_HOSTS': 'portal.example.cl',
            'FIELD_ENCRYPTION_KEY': Fernet.generate_key().decode(),
            'FIELD_ENCRYPTION_KEYS': '',
            'DATABASE_ENGINE': 'mysql',
            'DATABASE_NAME': 'example',
            'DATABASE_USER': 'example',
            'DATABASE_PASSWORD': 'example',
            'DATABASE_HOST': '127.0.0.1',
            'DATABASE_SSL_CA': '',
            'PORTAL_PUBLIC_URL': public_url,
            'PORTAL_CHANNEL_REDIS_URL': redis_url,
            'PORTAL_CACHE_URL': cache_url,
            'CORS_ALLOWED_ORIGINS': 'https://portal.example.cl',
            'CSRF_TRUSTED_ORIGINS': 'https://portal.example.cl',
            'JWT_COOKIE_SECURE': 'True',
            'SESSION_COOKIE_SECURE': 'True',
            'CSRF_COOKIE_SECURE': 'True',
            'SECURE_SSL_REDIRECT': 'True',
            'SECURE_HSTS_SECONDS': '31536000',
            'SECURE_HSTS_INCLUDE_SUBDOMAINS': 'True',
            'USE_X_FORWARDED_PROTO': 'True',
        })
        environment.update(overrides or {})
        for name in unset:
            environment.pop(name, None)
        return subprocess.run(
            [
                sys.executable,
                '-c',
                'from django.conf import settings; '
                'print(settings.PORTAL_PUBLIC_URL, settings.IS_PRODUCTION, settings.DEBUG, '
                'settings.REST_FRAMEWORK.get("DEFAULT_RENDERER_CLASSES"), '
                'settings.DATABASES["default"]["OPTIONS"])',
            ],
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

    def test_production_requires_shared_security_cache(self):
        result = self.check_production('https://portal.example.cl', cache_url='')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PORTAL_CACHE_URL', result.stderr)

    def test_production_rejects_reused_django_key_for_jwt(self):
        result = self.check_production(
            'https://portal.example.cl',
            reuse_django_key_for_jwt=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('JWT_SIGNING_KEY', result.stderr)

    def test_production_module_cannot_be_downgraded_by_environment(self):
        result = self.check_production(
            'https://portal.example.cl',
            overrides={'DJANGO_ENV': 'development', 'DJANGO_DEBUG': 'True'},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_DEBUG', result.stderr)

    def test_production_rejects_missing_or_weak_django_secret(self):
        missing = self.check_production(
            'https://portal.example.cl',
            overrides={'DJANGO_SECRET_KEY': ''},
        )
        weak = self.check_production(
            'https://portal.example.cl',
            overrides={'DJANGO_SECRET_KEY': 'django-insecure-example'},
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertNotEqual(weak.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY', missing.stderr)
        self.assertIn('DJANGO_SECRET_KEY', weak.stderr)

    def test_production_rejects_missing_or_invalid_fernet_key(self):
        missing = self.check_production(
            'https://portal.example.cl',
            overrides={'FIELD_ENCRYPTION_KEY': ''},
        )
        invalid = self.check_production(
            'https://portal.example.cl',
            overrides={'FIELD_ENCRYPTION_KEY': 'not-a-fernet-key'},
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn('FIELD_ENCRYPTION_KEY', missing.stderr)
        self.assertIn('FIELD_ENCRYPTION_KEY', invalid.stderr)

    def test_production_rejects_wildcard_hosts_and_cors(self):
        wildcard_host = self.check_production(
            'https://portal.example.cl',
            overrides={'DJANGO_ALLOWED_HOSTS': '*'},
        )
        wildcard_cors = self.check_production(
            'https://portal.example.cl',
            overrides={'CORS_ALLOWED_ORIGINS': '*'},
        )
        self.assertNotEqual(wildcard_host.returncode, 0)
        self.assertNotEqual(wildcard_cors.returncode, 0)
        self.assertIn('DJANGO_ALLOWED_HOSTS', wildcard_host.stderr)
        self.assertIn('CORS_ALLOWED_ORIGINS', wildcard_cors.stderr)

    def test_production_rejects_insecure_cookies_or_https(self):
        for variable in (
            'JWT_COOKIE_SECURE',
            'SESSION_COOKIE_SECURE',
            'CSRF_COOKIE_SECURE',
            'SECURE_SSL_REDIRECT',
            'USE_X_FORWARDED_PROTO',
        ):
            with self.subTest(variable=variable):
                result = self.check_production(
                    'https://portal.example.cl',
                    overrides={variable: 'False'},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(variable, result.stderr)

    def test_production_rejects_non_mysql_database(self):
        result = self.check_production(
            'https://portal.example.cl',
            overrides={'DATABASE_ENGINE': 'sqlite'},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DATABASE_ENGINE', result.stderr)

    def test_production_requires_ca_for_remote_mysql(self):
        result = self.check_production(
            'https://portal.example.cl',
            overrides={'DATABASE_HOST': 'mysql.internal.example', 'DATABASE_SSL_CA': ''},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DATABASE_SSL_CA', result.stderr)

    def test_remote_mysql_uses_ca_and_identity_verification(self):
        result = self.check_production(
            'https://portal.example.cl',
            overrides={
                'DATABASE_HOST': 'mysql.internal.example',
                'DATABASE_SSL_CA': str(Path(__file__).resolve()),
            },
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('VERIFY_IDENTITY', result.stdout)

    def test_production_rejects_redis_placeholder(self):
        result = self.check_production(
            'https://portal.example.cl',
            overrides={'PORTAL_CACHE_URL': 'replace-with-private-redis-cache-url'},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PORTAL_CACHE_URL', result.stderr)

    def test_production_rejects_cookie_scope_outside_auth(self):
        result = self.check_production(
            'https://portal.example.cl',
            overrides={'JWT_COOKIE_PATH': '/'},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('JWT_COOKIE_PATH', result.stderr)

    def test_production_uses_json_renderer_only(self):
        result = self.check_production(
            'https://portal.example.cl',
            overrides={},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('True False', result.stdout)
        self.assertIn('JSONRenderer', result.stdout)
