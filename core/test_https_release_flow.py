"""Flujo de sesión y ficha QR con HTTPS terminado en el proxy."""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Departamento, Equipamiento


@override_settings(
    ALLOWED_HOSTS=['portal.example.cl'],
    CSRF_TRUSTED_ORIGINS=['https://portal.example.cl'],
    DEBUG=False,
    IS_PRODUCTION=True,
    PORTAL_PUBLIC_URL='https://portal.example.cl',
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
    SECURE_SSL_REDIRECT=True,
    JWT_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SESSION_COOKIE_SECURE=True,
)
class HttpsReleaseFlowTests(TestCase):
    def setUp(self):
        User.objects.create_superuser('release-admin', password='TestPassword123!')
        Departamento.objects.create(nombre='Tecnología')
        self.asset = Equipamiento.objects.create(
            tipo='Notebook', marca='HP', modelo='840',
            numero_serie='RELEASE-QR-001', estado='STOCK',
        )
        self.client = APIClient(enforce_csrf_checks=True)
        self.proxy_headers = {
            'HTTP_HOST': 'portal.example.cl',
            'HTTP_X_FORWARDED_PROTO': 'https',
            'HTTP_ORIGIN': 'https://portal.example.cl',
        }

    def test_login_refresh_qr_and_logout_behind_https_proxy(self):
        path = f'/api/activos/qr/{self.asset.token_qr}/'
        self.assertEqual(self.client.get(path, **self.proxy_headers).status_code, 401)

        csrf = self.client.get('/api/auth/csrf/', **self.proxy_headers)
        self.assertEqual(csrf.status_code, 200)
        self.assertTrue(csrf.cookies['csrftoken']['secure'])
        csrf_token = csrf.json()['csrfToken']

        login = self.client.post(
            '/api/auth/login/',
            {'username': 'release-admin', 'password': 'TestPassword123!'},
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token,
            **self.proxy_headers,
        )
        self.assertEqual(login.status_code, 200, login.content)
        refresh_cookie = login.cookies['siminfra_refresh']
        self.assertTrue(refresh_cookie['secure'])
        self.assertTrue(refresh_cookie['httponly'])
        self.assertEqual(refresh_cookie['path'], '/api/auth/')

        qr = self.client.get(
            path, HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}",
            **self.proxy_headers,
        )
        self.assertEqual(qr.status_code, 200)
        self.assertEqual(
            qr.json()['qr_url'],
            f'https://portal.example.cl/qr/a/{self.asset.token_qr}',
        )
        summary = self.client.get(
            '/api/activos/resumen/',
            HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}",
            **self.proxy_headers,
        )
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()['conteos']['total'], 1)

        refreshed = self.client.post(
            '/api/auth/refresh/', {}, format='json',
            HTTP_X_CSRFTOKEN=csrf_token, **self.proxy_headers,
        )
        self.assertEqual(refreshed.status_code, 200, refreshed.content)
        self.assertTrue(refreshed.cookies['siminfra_refresh']['secure'])
        renewed_token = refreshed.json()['access']
        self.assertEqual(
            self.client.get(path, HTTP_AUTHORIZATION=f'Bearer {renewed_token}',
                            **self.proxy_headers).status_code,
            200,
        )

        logged_out = self.client.post(
            '/api/auth/logout/', {}, format='json',
            HTTP_X_CSRFTOKEN=csrf_token, **self.proxy_headers,
        )
        self.assertEqual(logged_out.status_code, 204)
        self.assertEqual(
            self.client.get(path, HTTP_AUTHORIZATION=f'Bearer {renewed_token}',
                            **self.proxy_headers).status_code,
            401,
        )
