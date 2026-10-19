from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Departamento, Equipamiento, PerfilGenerico, Usuario


class OptimisticConcurrencyTests(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user(
            'concurrency-admin',
            password='StrongPass!123',
        )
        self.admin.groups.add(admin_group)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.department = Departamento.objects.create(nombre='Concurrencia')

    def test_stale_profile_update_returns_409_and_preserves_first_change(self):
        profile = PerfilGenerico.objects.create(
            nombre='Perfil Inicial',
            usuario='perfil.concurrente',
            departamento=self.department,
        )
        url = f'/api/perfiles-genericos/{profile.pk}/'
        original_version = self.client.get(url).data['version']

        first = self.client.patch(url, {
            'nombre': 'Cambio Primera Sesión',
            'version': original_version,
        }, format='json')
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data['version'], original_version + 1)

        stale = self.client.patch(url, {
            'nombre': 'Cambio Segunda Sesión',
            'version': original_version,
        }, format='json')
        self.assertEqual(stale.status_code, 409, stale.data)
        self.assertEqual(stale.data['code'], 'stale_update')
        self.assertEqual(int(stale.data['current_version']), original_version + 1)

        profile.refresh_from_db()
        self.assertEqual(profile.nombre, 'Cambio Primera Sesión')

    def test_related_release_invalidates_an_open_equipment_form(self):
        user = Usuario.objects.create(
            nombre_completo='Persona Concurrente',
            usuario_red='persona.concurrente',
            correo_corp='concurrente@example.com',
            departamento=self.department,
        )
        equipment = Equipamiento.objects.create(
            usuario=user,
            tipo='Notebook',
            marca='Lenovo',
            modelo='T14',
            numero_serie='CONCURRENT-1',
        )
        stale_version = equipment.version

        user.estado = 'BAJA'
        user.save(update_fields=['estado'])
        equipment.refresh_from_db()
        self.assertGreater(equipment.version, stale_version)
        self.assertIsNone(equipment.usuario_id)

        response = self.client.patch(f'/api/equipos/{equipment.pk}/', {
            'modelo': 'Cambio Obsoleto',
            'version': stale_version,
        }, format='json')
        self.assertEqual(response.status_code, 409, response.data)
        equipment.refresh_from_db()
        self.assertEqual(equipment.modelo, 'T14')

    def test_partial_model_save_increments_version(self):
        original_version = self.department.version
        self.department.nombre = 'Concurrencia Actualizada'
        self.department.save(update_fields=['nombre'])
        self.assertEqual(self.department.version, original_version + 1)

    def test_queryset_update_increments_version(self):
        original_version = self.department.version
        Departamento.objects.filter(pk=self.department.pk).update(activo=False)
        self.department.refresh_from_db()
        self.assertEqual(self.department.version, original_version + 1)
        self.assertFalse(self.department.activo)

