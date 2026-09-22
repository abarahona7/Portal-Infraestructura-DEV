from django.contrib.auth.models import User, Group
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from cryptography.fernet import Fernet
from core.models import Usuario, PerfilGenerico, IP, Equipamiento, Anexo, SecurityAuditLog

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
