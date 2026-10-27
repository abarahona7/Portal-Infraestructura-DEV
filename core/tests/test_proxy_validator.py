from django.test import SimpleTestCase

from scripts.validar_proxy_publicacion import (
    validate_hsts_policy,
    validate_installed_configuration,
)


class ProxySecurityValidatorTests(SimpleTestCase):
    def test_accepts_current_hsts_policy(self):
        validate_hsts_policy('max-age=31536000; includeSubDomains')

    def test_rejects_weak_or_unapproved_hsts_policy(self):
        invalid_values = (
            'max-age=86400; includeSubDomains',
            'max-age=31536000',
            'max-age=31536000; includeSubDomains; preload',
        )
        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(AssertionError):
                validate_hsts_policy(value)

    def test_rejects_example_domain_in_installed_configuration(self):
        configuration = '''
            server_name portal.example.cl;
            add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        '''
        with self.assertRaises(AssertionError):
            validate_installed_configuration(configuration, require_hsts=True)

    def test_accepts_installed_configuration_without_placeholders(self):
        configuration = '''
            # Sustituir portal.example.cl antes de instalar.
            server_name portal.infra.test;
            add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
        '''
        validate_installed_configuration(configuration, require_hsts=True)
