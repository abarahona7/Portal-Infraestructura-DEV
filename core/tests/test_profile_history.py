from django.apps import apps
from django.contrib.auth.models import Group, User
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from core.management.commands.limpiar_datos_v11 import DELETE_ORDER
from core.models import (
    Departamento,
    HistorialPerfilGenerico,
    PerfilGenerico,
)


class ProfileHistoryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user(
            'profile-history-admin',
            password='StrongPass!123',
        )
        self.admin.groups.add(admin_group)
        self.client.force_authenticate(user=self.admin)
        self.department = Departamento.objects.create(nombre='Perfiles Auditados')

    def test_profile_lifecycle_is_audited_without_exposing_passwords(self):
        created = self.client.post(
            '/api/perfiles-genericos/',
            {
                'nombre': 'Perfil Auditado',
                'usuario': 'perfil.auditado',
                'password': 'ClaveInicial123',
                'departamento': self.department.pk,
                'tipo': 'On Premise',
                'estado': 'ACTIVO',
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        profile_id = created.json()['id']
        creation_history = HistorialPerfilGenerico.objects.get(
            perfil_id=profile_id,
            accion='CREACION',
        )
        self.assertEqual(creation_history.modificado_por, self.admin.username)

        updated = self.client.patch(
            f'/api/perfiles-genericos/{profile_id}/',
            {
                'nombre': 'Perfil Auditado Actualizado',
                'password': 'ClaveNueva456',
                'estado': 'INACTIVO',
            },
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        changed_history = HistorialPerfilGenerico.objects.get(
            perfil_id=profile_id,
            accion='MODIFICACION',
        )
        self.assertEqual(changed_history.modificado_por, self.admin.username)
        self.assertIn('Estado:::ACTIVO:::INACTIVO', changed_history.observacion)
        self.assertIn('ContraseÃ±a:::', changed_history.observacion)
        self.assertNotIn('ClaveInicial123', changed_history.observacion)
        self.assertNotIn('ClaveNueva456', changed_history.observacion)

        listed = self.client.get('/api/perfiles-genericos/')
        self.assertEqual(listed.status_code, 200)
        first_result = listed.json()['results'][0]
        self.assertNotIn('historial', first_result)

        detail = self.client.get(f'/api/perfiles-genericos/{profile_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            [entry['accion'] for entry in detail.json()['historial']],
            ['MODIFICACION', 'CREACION'],
        )

        deleted = self.client.delete(f'/api/perfiles-genericos/{profile_id}/')
        self.assertEqual(deleted.status_code, 204)
        deletion_history = HistorialPerfilGenerico.objects.get(
            perfil_id=profile_id,
            perfil_usuario='perfil.auditado',
            accion='ARCHIVO',
        )
        self.assertEqual(deletion_history.modificado_por, self.admin.username)
        self.assertFalse(PerfilGenerico.objects.filter(pk=profile_id).exists())
        self.assertTrue(PerfilGenerico.all_objects.filter(pk=profile_id).exists())

    def test_cleanup_command_tracks_every_core_model(self):
        configured_models = set(apps.get_app_config('core').get_models())
        self.assertEqual(configured_models, set(DELETE_ORDER))


class ProfileHistoryRollbackTests(TransactionTestCase):
    def setUp(self):
        self.department = Departamento.objects.create(nombre='Rollback Perfil')
        self.first = PerfilGenerico.objects.create(
            nombre='Perfil Primero',
            usuario='perfil.primero',
            departamento=self.department,
        )
        self.second = PerfilGenerico.objects.create(
            nombre='Perfil Segundo',
            usuario='perfil.segundo',
            departamento=self.department,
        )

    def test_failed_unique_update_does_not_leave_false_history(self):
        history_count = HistorialPerfilGenerico.objects.filter(
            perfil=self.first
        ).count()
        self.first.usuario = self.second.usuario.upper()

        with self.assertRaises(IntegrityError):
            self.first.save()

        self.assertEqual(
            HistorialPerfilGenerico.objects.filter(perfil=self.first).count(),
            history_count,
        )
        self.first.refresh_from_db()
        self.assertEqual(self.first.usuario, 'perfil.primero')
