from django.contrib.auth.models import User, Group
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from cryptography.fernet import Fernet
from core.models import Usuario, PerfilGenerico, IP, Equipamiento, Anexo, SecurityAuditLog, Departamento, SubArea

@override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode(), LEGACY_DJANGO_SECRET_KEY='legacy-key')
class SecurityTests(TestCase):
    def setUp(self):
        self.client=APIClient()
        for name in ['Visualizador','Operador Infraestructura','Administrador']:
            Group.objects.get_or_create(name=name)
        self.viewer=User.objects.create_user('viewer',password='StrongPass!123'); self.viewer.groups.add(Group.objects.get(name='Visualizador'))
        self.operator=User.objects.create_user('operator',password='StrongPass!123'); self.operator.groups.add(Group.objects.get(name='Operador Infraestructura'))
        self.admin=User.objects.create_user('adminx',password='StrongPass!123'); self.admin.groups.add(Group.objects.get(name='Administrador'))
        self.portal_user=Usuario.objects.create(nombre_completo='Persona Uno',usuario_red='puno',correo_corp='puno@example.com',dpto_area='TI',password_gmail='Secret123')

    def auth(self,user): self.client.force_authenticate(user=user)

    def test_unauthenticated_private_api_denied(self):
        self.assertEqual(self.client.get('/api/usuarios/').status_code,401)

    def test_viewer_cannot_modify(self):
        self.auth(self.viewer)
        r=self.client.post('/api/ips/', {'direccion_ip':'10.0.0.1','estado':'LIBRE'}, format='json')
        self.assertEqual(r.status_code,403)


    def test_viewer_can_only_read_anexos(self):
        Anexo.objects.create(numero_anexo='4321')
        self.auth(self.viewer)

        allowed = self.client.get('/api/anexos/')
        denied_users = self.client.get('/api/usuarios/')
        denied_ips = self.client.get('/api/ips/')
        denied_write = self.client.post(
            '/api/anexos/',
            {'numero_anexo': '4322', 'estado': 'DISPONIBLE'},
            format='json',
        )

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(denied_users.status_code, 403)
        self.assertEqual(denied_ips.status_code, 403)
        self.assertEqual(denied_write.status_code, 403)

    def test_operator_can_create_but_not_delete(self):
        self.auth(self.operator)
        r=self.client.post('/api/ips/', {'direccion_ip':'10.0.0.2','estado':'LIBRE'}, format='json')
        self.assertEqual(r.status_code,201)
        self.assertEqual(self.client.delete(f"/api/ips/{r.data['id']}/").status_code,403)

    def test_normal_get_does_not_expose_secret(self):
        self.auth(self.admin)
        data=self.client.get(f'/api/usuarios/{self.portal_user.pk}/').json()
        self.assertNotIn('password_gmail',data)
        self.assertTrue(data['password_gmail_configured'])

    def test_operator_cannot_reveal(self):
        self.auth(self.operator)
        r=self.client.post('/api/secrets/reveal/', {'module':'usuario','object_id':self.portal_user.pk,'secret_type':'password_gmail','password':'StrongPass!123'}, format='json')
        self.assertEqual(r.status_code,403)

    def test_admin_reveal_requires_correct_reauthentication(self):
        self.auth(self.admin)
        bad=self.client.post('/api/secrets/reveal/', {'module':'usuario','object_id':self.portal_user.pk,'secret_type':'password_gmail','password':'wrong'}, format='json')
        self.assertEqual(bad.status_code,403)
        good=self.client.post('/api/secrets/reveal/', {'module':'usuario','object_id':self.portal_user.pk,'secret_type':'password_gmail','password':'StrongPass!123'}, format='json')
        self.assertEqual(good.status_code,200); self.assertEqual(good.json()['secret'],'Secret123')
        self.assertEqual(good['Cache-Control'],'no-store, private')
        self.assertTrue(SecurityAuditLog.objects.filter(event='SECRET_REVEAL', success=True).exists())

    def test_blank_secret_update_preserves_existing(self):
        self.auth(self.operator)
        before=self.portal_user.password_gmail
        r=self.client.patch(f'/api/usuarios/{self.portal_user.pk}/', {'password_gmail':''}, format='json')
        self.assertEqual(r.status_code,200)
        self.portal_user.refresh_from_db(); self.assertEqual(self.portal_user.password_gmail,before)

    def test_ip_state_rules(self):
        ip=IP.objects.create(direccion_ip='10.0.0.3',usuario=self.portal_user)
        self.assertEqual(ip.estado,'RESERVADA')
        ip.usuario=None; ip.asignado_otro='CCTV'; ip.save(); self.assertEqual(ip.estado,'RESERVADA')
        ip.asignado_otro=''; ip.save(); self.assertEqual(ip.estado,'LIBRE')

    def test_baja_releases_assets(self):
        eq=Equipamiento.objects.create(usuario=self.portal_user,tipo='Notebook',marca='X',modelo='Y',numero_serie='SER-1')
        ip=IP.objects.create(direccion_ip='10.0.0.4',usuario=self.portal_user)
        self.portal_user.estado='BAJA'; self.portal_user.save(); eq.refresh_from_db(); ip.refresh_from_db()
        self.assertIsNone(eq.usuario); self.assertEqual(eq.estado,'STOCK'); self.assertIsNone(ip.usuario); self.assertEqual(ip.estado,'LIBRE')

    def test_usuario_red_duplicate_is_case_insensitive(self):
        self.auth(self.admin)
        response = self.client.post(
            '/api/usuarios/',
            {
                'nombre_completo': 'Persona Dos',
                'usuario_red': '  PUNO  ',
                'correo_corp': 'persona.dos@example.com',
                'dpto_area': 'TI',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('usuario_red', response.json())

    def test_departamento_duplicate_is_case_and_space_insensitive(self):
        self.auth(self.admin)
        first = self.client.post(
            '/api/departamentos/',
            {'nombre': 'Gerencia'},
            format='json',
        )
        duplicate = self.client.post(
            '/api/departamentos/',
            {'nombre': '  GERENCIA  '},
            format='json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(Departamento.objects.count(), 1)

    def test_subarea_unique_inside_department(self):
        self.auth(self.admin)
        tecnologia = Departamento.objects.create(nombre='Tecnología')
        operaciones = Departamento.objects.create(nombre='Operaciones')

        first = self.client.post(
            '/api/subareas/',
            {
                'departamento': tecnologia.pk,
                'nombre': 'Infraestructura',
            },
            format='json',
        )
        duplicate = self.client.post(
            '/api/subareas/',
            {
                'departamento': tecnologia.pk,
                'nombre': 'INFRAESTRUCTURA',
            },
            format='json',
        )
        other_department = self.client.post(
            '/api/subareas/',
            {
                'departamento': operaciones.pk,
                'nombre': 'Infraestructura',
            },
            format='json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(other_department.status_code, 201)
        self.assertEqual(SubArea.objects.count(), 2)

    def test_usuario_rejects_subarea_from_other_department(self):
        self.auth(self.admin)
        tecnologia = Departamento.objects.create(nombre='Tecnología')
        operaciones = Departamento.objects.create(nombre='Operaciones')
        infraestructura = SubArea.objects.create(
            departamento=tecnologia,
            nombre='Infraestructura',
        )

        response = self.client.post(
            '/api/usuarios/',
            {
                'nombre_completo': 'Persona Tres',
                'usuario_red': 'ptres',
                'correo_corp': 'ptres@example.com',
                'departamento': operaciones.pk,
                'subarea': infraestructura.pk,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('subarea', response.json())

    def test_admin_can_delete_unused_subarea(self):
        self.auth(self.admin)
        departamento = Departamento.objects.create(nombre='Tecnología')
        subarea = SubArea.objects.create(
            departamento=departamento,
            nombre='Temporal',
        )

        response = self.client.delete(f'/api/subareas/{subarea.pk}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(SubArea.objects.filter(pk=subarea.pk).exists())

    def test_admin_cannot_delete_subarea_in_use(self):
        self.auth(self.admin)
        departamento = Departamento.objects.create(nombre='Tecnología')
        subarea = SubArea.objects.create(
            departamento=departamento,
            nombre='Infraestructura',
        )
        self.portal_user.departamento = departamento
        self.portal_user.subarea = subarea
        self.portal_user.save()

        response = self.client.delete(f'/api/subareas/{subarea.pk}/')

        self.assertEqual(response.status_code, 400)
        self.assertTrue(SubArea.objects.filter(pk=subarea.pk).exists())
        self.assertIn('detail', response.json())

    def test_admin_can_delete_empty_department_but_not_one_with_subareas(self):
        self.auth(self.admin)
        empty_department = Departamento.objects.create(nombre='Temporal')
        used_structure = Departamento.objects.create(nombre='Operaciones')
        SubArea.objects.create(
            departamento=used_structure,
            nombre='Arriendo y Patentes',
        )

        deleted = self.client.delete(
            f'/api/departamentos/{empty_department.pk}/'
        )
        blocked = self.client.delete(
            f'/api/departamentos/{used_structure.pk}/'
        )

        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(blocked.status_code, 400)
        self.assertTrue(Departamento.objects.filter(pk=used_structure.pk).exists())
