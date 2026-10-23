from io import StringIO

from cryptography.fernet import Fernet, InvalidToken
from django.core.management import call_command
from django.test import TestCase, override_settings

from core.crypto import ENC_V2, decrypt_val, encrypt_val, needs_rotation, rotate_value
from core.models import Departamento, Usuario


class MultiFernetRotationTests(TestCase):
    def setUp(self):
        self.old_key = Fernet.generate_key().decode()
        self.new_key = Fernet.generate_key().decode()

    def test_old_ciphertext_remains_readable_and_new_writes_use_primary(self):
        with override_settings(
            FIELD_ENCRYPTION_KEY=self.old_key,
            FIELD_ENCRYPTION_KEYS=[self.old_key],
        ):
            old_value = encrypt_val('secreto-sintetico')

        with override_settings(
            FIELD_ENCRYPTION_KEY=self.new_key,
            FIELD_ENCRYPTION_KEYS=[self.new_key, self.old_key],
        ):
            self.assertEqual(decrypt_val(old_value), 'secreto-sintetico')
            self.assertTrue(needs_rotation(old_value))
            new_value = encrypt_val('nuevo-secreto-sintetico')
            rotated = rotate_value(old_value)
            self.assertFalse(needs_rotation(rotated))

        new_fernet = Fernet(self.new_key.encode())
        self.assertEqual(
            new_fernet.decrypt(new_value[len(ENC_V2):].encode()).decode(),
            'nuevo-secreto-sintetico',
        )
        self.assertEqual(
            new_fernet.decrypt(rotated[len(ENC_V2):].encode()).decode(),
            'secreto-sintetico',
        )
        with self.assertRaises(InvalidToken):
            Fernet(self.old_key.encode()).decrypt(rotated[len(ENC_V2):].encode())

    def test_rotation_command_is_dry_run_by_default(self):
        department = Departamento.objects.create(nombre='Rotación QA')
        with override_settings(
            FIELD_ENCRYPTION_KEY=self.old_key,
            FIELD_ENCRYPTION_KEYS=[self.old_key],
        ):
            old_value = encrypt_val('secreto-a-rotar')
        person = Usuario.objects.create(
            nombre_completo='Persona Rotación',
            usuario_red='rotacion.qa',
            departamento=department,
        )
        Usuario.objects.filter(pk=person.pk).update(password_gmail=old_value)

        settings_override = override_settings(
            FIELD_ENCRYPTION_KEY=self.new_key,
            FIELD_ENCRYPTION_KEYS=[self.new_key, self.old_key],
        )
        with settings_override:
            dry_output = StringIO()
            call_command('rotate_secrets', stdout=dry_output)
            person.refresh_from_db()
            self.assertEqual(person.password_gmail, old_value)
            self.assertIn('Secretos por rotar: 1', dry_output.getvalue())

            apply_output = StringIO()
            call_command(
                'rotate_secrets', apply=True,
                confirm='ROTATE_ENCRYPTION_KEYS', stdout=apply_output,
            )
            person.refresh_from_db()
            self.assertNotEqual(person.password_gmail, old_value)
            self.assertEqual(decrypt_val(person.password_gmail), 'secreto-a-rotar')
            self.assertIn('Secretos rotados: 1', apply_output.getvalue())
