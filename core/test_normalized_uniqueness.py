from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import (
    Equipamiento,
    PCGenerico,
    PerfilGenerico,
    Servidor,
    Usuario,
)
from core.serializers import (
    EquipamientoSerializer,
    PerfilGenericoSerializer,
    ServidorSerializer,
    UsuarioSerializer,
)


class NormalizedUniquenessTests(TestCase):
    def assert_database_rejects(self, create_record):
        with self.assertRaises(IntegrityError), transaction.atomic():
            create_record()

    def test_user_identity_is_unique_after_normalizing_case_and_spaces(self):
        user = Usuario.objects.create(
            nombre_completo='  Ana   Perez  ',
            usuario_red=' APEREZ ',
            correo_corp=' APEREZ@EXAMPLE.COM ',
        )

        self.assertEqual(user.nombre_completo, 'Ana Perez')
        self.assertEqual(user.nombre_completo_normalizado, 'ana perez')
        self.assertEqual(user.usuario_red_normalizado, 'aperez')
        self.assertEqual(user.correo_corp_normalizado, 'aperez@example.com')

        self.assert_database_rejects(lambda: Usuario.objects.create(
            nombre_completo='ana perez',
            usuario_red='otra-cuenta',
            correo_corp='otra-cuenta@example.com',
        ))

    def test_server_hostname_is_unique_without_changing_visible_case(self):
        server = Servidor.objects.create(hostname=' SRV-APP-01 ')

        self.assertEqual(server.hostname, 'SRV-APP-01')
        self.assertEqual(server.hostname_normalizado, 'srv-app-01')
        self.assert_database_rejects(lambda: Servidor.objects.create(
            hostname='srv-app-01',
        ))

    def test_equipment_identifiers_are_unique_and_computer_hostname_is_scoped(self):
        equipment = Equipamiento.objects.create(
            tipo='Notebook',
            marca='Lenovo',
            modelo='T14',
            numero_serie=' SER-ABC ',
            af=' AF100 ',
            hostname=' NB-SOPORTE-01 ',
        )

        self.assertEqual(equipment.numero_serie, 'SER-ABC')
        self.assertEqual(equipment.numero_serie_normalizado, 'ser-abc')
        self.assertEqual(equipment.af_normalizado, 'af100')
        self.assertEqual(
            equipment.hostname_computador_normalizado,
            'nb-soporte-01',
        )

        self.assert_database_rejects(lambda: Equipamiento.objects.create(
            tipo='Celular',
            marca='Apple',
            modelo='iPhone',
            numero_serie='ser-abc',
        ))
        self.assert_database_rejects(lambda: Equipamiento.objects.create(
            tipo='Tablet',
            marca='Samsung',
            modelo='Tab',
            numero_serie='SER-OTRA',
            af='af100',
        ))
        self.assert_database_rejects(lambda: Equipamiento.objects.create(
            tipo='Mac',
            marca='Apple',
            modelo='MacBook',
            numero_serie='SER-MAC',
            hostname='nb-soporte-01',
        ))

        phone = Equipamiento.objects.create(
            tipo='Celular',
            marca='Apple',
            modelo='iPhone',
            numero_serie='SER-PHONE',
            hostname='NB-SOPORTE-01',
        )
        self.assertIsNone(phone.hostname_computador_normalizado)

    def test_generic_profile_and_pc_identifiers_are_unique(self):
        profile = PerfilGenerico.objects.create(
            nombre='Correo soporte',
            usuario=' Soporte.Simi ',
        )
        pc = PCGenerico.objects.create(
            usuario_local='soporte.local',
            hostname=' PC-SOPORTE-01 ',
            numero_serie=' PC-SER-01 ',
            activo_fijo=' PC100 ',
        )

        self.assertEqual(profile.usuario, 'Soporte.Simi')
        self.assertEqual(profile.usuario_normalizado, 'soporte.simi')
        self.assertEqual(pc.hostname_normalizado, 'pc-soporte-01')
        self.assertEqual(pc.numero_serie_normalizado, 'pc-ser-01')
        self.assertEqual(pc.activo_fijo_normalizado, 'pc100')

        self.assert_database_rejects(lambda: PerfilGenerico.objects.create(
            nombre='Otro perfil',
            usuario='soporte.simi',
        ))
        self.assert_database_rejects(lambda: PCGenerico.objects.create(
            usuario_local='otra.local',
            hostname='pc-soporte-01',
        ))

    def test_internal_normalized_fields_are_not_exposed_by_api_serializers(self):
        user = Usuario.objects.create(
            nombre_completo='Persona API',
            usuario_red='persona.api',
            correo_corp='persona.api@example.com',
        )
        server = Servidor.objects.create(hostname='SRV-API')
        equipment = Equipamiento.objects.create(
            tipo='Notebook',
            marca='Dell',
            modelo='Latitude',
            numero_serie='API-EQ-01',
        )
        profile = PerfilGenerico.objects.create(
            nombre='Perfil API',
            usuario='perfil.api',
        )

        payloads = (
            UsuarioSerializer(user).data,
            ServidorSerializer(server).data,
            EquipamientoSerializer(equipment).data,
            PerfilGenericoSerializer(profile).data,
        )
        for payload in payloads:
            self.assertFalse(any(key.endswith('normalizado') for key in payload))

