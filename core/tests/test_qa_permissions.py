"""Matriz de acceso comprobada directamente en la API, sin depender de la UI."""

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Anexo, Departamento, Equipamiento, Usuario


@override_settings(PORTAL_PUBLIC_URL='https://portal.qa.example.cl')
class QAMatrizRolesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.users = {}
        for role in ('Visualizador', 'Operador Infraestructura', 'Administrador'):
            account = User.objects.create_user(
                username=f'qa-{role.split()[0].lower()}', password='TestPassword123!',
            )
            account.groups.add(Group.objects.get_or_create(name=role)[0])
            self.users[role] = account
        self.users['Superusuario'] = User.objects.create_superuser(
            'qa-superusuario', password='TestPassword123!',
        )
        department = Departamento.objects.create(nombre='Departamento Roles QA')
        self.person = Usuario.objects.create(
            nombre_completo='Persona Roles QA', usuario_red='roles.qa',
            correo_corp='roles.qa@example.com', departamento=department,
        )
        self.equipment = Equipamiento.objects.create(
            usuario=self.person, tipo='Notebook', marca='Dell', modelo='7400',
            numero_serie='QA-PERM-01', estado='ASIGNADO',
        )
        self.extension = Anexo.objects.create(numero_anexo='8601')

    def authenticate(self, role):
        self.client.force_authenticate(user=self.users[role] if role else None)

    def test_visualizador_solo_consulta_anexos_y_nunca_puede_escribir(self):
        self.authenticate('Visualizador')
        self.assertEqual(self.client.get('/api/anexos/').status_code, 200)
        detail = self.client.get(f'/api/anexos/{self.extension.pk}/')
        self.assertEqual(detail.status_code, 200)
        self.assertIn('historial', detail.data)

        protected = (
            '/api/usuarios/', '/api/departamentos/', '/api/subareas/',
            '/api/equipos/', '/api/pcs-genericos/', '/api/ips/',
            '/api/servidores/', '/api/perfiles-genericos/',
            '/api/activos/resumen/',
            f'/api/activos/qr/{self.equipment.token_qr}/',
            f'/api/activos/qr/{self.equipment.token_qr}/imagen/',
            f'/api/usuarios/{self.person.pk}/acta-entrega/',
        )
        for path in protected:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

        self.assertEqual(self.client.post(
            '/api/anexos/', {'numero_anexo': '8602'}, format='json',
        ).status_code, 403)
        self.assertEqual(self.client.patch(
            f'/api/anexos/{self.extension.pk}/', {'exterior': '+56212345678'},
            format='json',
        ).status_code, 403)
        self.assertEqual(self.client.delete(
            f'/api/anexos/{self.extension.pk}/',
        ).status_code, 403)
        self.assertEqual(Anexo.objects.count(), 1)

    def test_operador_consulta_todos_los_modulos_pero_no_elimina(self):
        self.authenticate('Operador Infraestructura')
        modules = (
            'usuarios', 'departamentos', 'subareas', 'equipos',
            'pcs-genericos', 'ips', 'servidores', 'anexos', 'perfiles-genericos',
        )
        for module in modules:
            with self.subTest(module=module, action='read'):
                self.assertEqual(self.client.get(f'/api/{module}/').status_code, 200)
            with self.subTest(module=module, action='delete'):
                self.assertEqual(self.client.delete(f'/api/{module}/999999/').status_code, 403)
        self.assertEqual(self.client.get('/api/activos/resumen/').status_code, 200)
        self.assertEqual(self.client.get(
            f'/api/activos/qr/{self.equipment.token_qr}/',
        ).status_code, 200)
        self.assertEqual(self.client.post(
            '/api/secrets/reveal/',
            {'module': 'equipamiento', 'object_id': self.equipment.pk,
             'secret_type': 'pin', 'password': 'TestPassword123!'},
            format='json',
        ).status_code, 403)

    def test_administrador_y_superusuario_pueden_eliminar_recurso_libre(self):
        for index, role in enumerate(('Administrador', 'Superusuario'), 1):
            with self.subTest(role=role):
                extension = Anexo.objects.create(numero_anexo=f'861{index}')
                self.authenticate(role)
                self.assertEqual(self.client.get('/api/activos/resumen/').status_code, 200)
                self.assertEqual(self.client.get(
                    f'/api/activos/qr/{self.equipment.token_qr}/',
                ).status_code, 200)
                self.assertEqual(self.client.delete(
                    f'/api/anexos/{extension.pk}/',
                ).status_code, 204)
                self.assertFalse(Anexo.objects.filter(pk=extension.pk).exists())

    def test_tablero_y_ficha_qr_exigen_sesion(self):
        self.authenticate(None)
        for path in (
            '/api/activos/resumen/',
            f'/api/activos/qr/{self.equipment.token_qr}/',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)
