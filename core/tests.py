from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from cryptography.fernet import Fernet
from core.models import Usuario, PerfilGenerico, IP, Equipamiento, Anexo, SecurityAuditLog, Departamento, SubArea, PCGenerico, PortalSession, Servidor

@override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode(), LEGACY_DJANGO_SECRET_KEY='legacy-key')
class SecurityTests(TestCase):
    def setUp(self):
        self.client=APIClient()
        self.department = Departamento.objects.create(nombre='Pruebas Generales')
        for name in ['Visualizador','Operador Infraestructura','Administrador']:
            Group.objects.get_or_create(name=name)
        self.viewer=User.objects.create_user('viewer',password='StrongPass!123'); self.viewer.groups.add(Group.objects.get(name='Visualizador'))
        self.operator=User.objects.create_user('operator',password='StrongPass!123'); self.operator.groups.add(Group.objects.get(name='Operador Infraestructura'))
        self.admin=User.objects.create_user('adminx',password='StrongPass!123'); self.admin.groups.add(Group.objects.get(name='Administrador'))
        self.portal_user=Usuario.objects.create(nombre_completo='Persona Uno',usuario_red='puno',correo_corp='puno@example.com',departamento=self.department,password_gmail='Secret123')

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
        r=self.client.post('/api/ips/', {'direccion_ip':'172.23.1.2','estado':'LIBRE'}, format='json')
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
                'departamento': self.department.pk,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('usuario_red', response.json())

    def test_departamento_duplicate_is_case_and_space_insensitive(self):
        self.auth(self.admin)
        initial_count = Departamento.objects.count()
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
        self.assertEqual(Departamento.objects.count(), initial_count + 1)

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

    def test_ip_rejects_unknown_segment(self):
        self.auth(self.admin)
        response = self.client.post(
            '/api/ips/',
            {'direccion_ip': '10.0.0.50', 'asignado_otro': 'Prueba'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('direccion_ip', response.json())
        self.assertFalse(IP.objects.filter(direccion_ip='10.0.0.50').exists())

    def test_ip_api_cannot_assign_user_directly(self):
        self.auth(self.admin)
        response = self.client.post(
            '/api/ips/',
            {
                'direccion_ip': '172.23.1.60',
                'usuario': self.portal_user.pk,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('usuario', response.json())
        self.assertFalse(IP.objects.filter(direccion_ip='172.23.1.60').exists())

    def test_ip_status_is_automatic_for_other_assignment(self):
        self.auth(self.admin)
        created = self.client.post(
            '/api/ips/',
            {
                'direccion_ip': '172.23.1.61',
                'estado': 'LIBRE',
                'asignado_otro': 'Impresora Piso 2',
            },
            format='json',
        )

        self.assertEqual(created.status_code, 201)
        ip = IP.objects.get(direccion_ip='172.23.1.61')
        self.assertEqual(ip.estado, 'RESERVADA')

        updated = self.client.patch(
            f'/api/ips/{ip.pk}/',
            {'asignado_otro': ''},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        ip.refresh_from_db()
        self.assertEqual(ip.estado, 'LIBRE')

    def test_admin_cannot_delete_ip_assigned_to_user(self):
        self.auth(self.admin)
        ip = IP.objects.create(
            direccion_ip='172.23.1.62',
            usuario=self.portal_user,
        )

        blocked = self.client.delete(f'/api/ips/{ip.pk}/')
        self.assertEqual(blocked.status_code, 400)
        self.assertTrue(IP.objects.filter(pk=ip.pk).exists())

        ip.usuario = None
        ip.save()
        deleted = self.client.delete(f'/api/ips/{ip.pk}/')
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(IP.objects.filter(pk=ip.pk).exists())

    def test_usuario_can_have_only_one_ip(self):
        self.auth(self.admin)
        first_ip = IP.objects.create(direccion_ip='172.23.1.70')
        second_ip = IP.objects.create(direccion_ip='172.23.1.71')

        first_assignment = self.client.patch(
            f'/api/usuarios/{self.portal_user.pk}/',
            {'ip_seleccionada': first_ip.direccion_ip},
            format='json',
        )
        self.assertEqual(first_assignment.status_code, 200)

        second_assignment = self.client.patch(
            f'/api/usuarios/{self.portal_user.pk}/',
            {'ip_seleccionada': second_ip.direccion_ip},
            format='json',
        )
        self.assertEqual(second_assignment.status_code, 200)

        first_ip.refresh_from_db()
        second_ip.refresh_from_db()
        self.assertIsNone(first_ip.usuario)
        self.assertEqual(first_ip.estado, 'LIBRE')
        self.assertEqual(second_ip.usuario_id, self.portal_user.pk)
        self.assertEqual(second_ip.estado, 'RESERVADA')
        self.assertEqual(IP.objects.filter(usuario=self.portal_user).count(), 1)

    def test_usuario_can_release_ip_with_null(self):
        self.auth(self.admin)
        ip = IP.objects.create(direccion_ip='172.23.1.74', usuario=self.portal_user)

        response = self.client.patch(
            f'/api/usuarios/{self.portal_user.pk}/',
            {'ip_seleccionada': None},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        ip.refresh_from_db()
        self.assertIsNone(ip.usuario_id)
        self.assertEqual(ip.estado, 'LIBRE')

    def test_baja_user_cannot_receive_ip(self):
        self.auth(self.admin)
        self.portal_user.estado = 'BAJA'
        self.portal_user.save()
        ip = IP.objects.create(direccion_ip='172.23.1.72')

        response = self.client.patch(
            f'/api/usuarios/{self.portal_user.pk}/',
            {'ip_seleccionada': ip.direccion_ip},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('ip_seleccionada', response.json())
        ip.refresh_from_db()
        self.assertIsNone(ip.usuario)
        self.assertEqual(ip.estado, 'LIBRE')

    def test_licencia_user_cannot_receive_new_ip(self):
        self.auth(self.admin)
        self.portal_user.estado = 'LICENCIA'
        self.portal_user.save()
        ip = IP.objects.create(direccion_ip='172.23.1.73')

        response = self.client.patch(
            f'/api/usuarios/{self.portal_user.pk}/',
            {'ip_seleccionada': ip.direccion_ip},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('ip_seleccionada', response.json())
        ip.refresh_from_db()
        self.assertIsNone(ip.usuario)
        self.assertEqual(ip.estado, 'LIBRE')
    def test_perfil_generico_uses_departamento_and_subarea(self):
        self.auth(self.admin)
        departamento = Departamento.objects.create(nombre='Tecnología')
        subarea = SubArea.objects.create(
            departamento=departamento,
            nombre='Infraestructura',
        )

        response = self.client.post(
            '/api/perfiles-genericos/',
            {
                'nombre': 'Soporte Infra',
                'usuario': 'perfil.infra',
                'tipo': 'On Premise',
                'departamento': departamento.pk,
                'subarea': subarea.pk,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['departamento_nombre'], 'Tecnología')
        self.assertEqual(response.data['subarea_nombre'], 'Infraestructura')

        perfil = PerfilGenerico.objects.get(pk=response.data['id'])
        self.assertEqual(perfil.departamento_id, departamento.pk)
        self.assertEqual(perfil.subarea_id, subarea.pk)
        self.assertEqual(perfil.dpto_area, 'Infraestructura')

    def test_perfil_generico_rejects_subarea_from_other_department(self):
        self.auth(self.admin)
        tecnologia = Departamento.objects.create(nombre='Tecnología')
        operaciones = Departamento.objects.create(nombre='Operaciones')
        infraestructura = SubArea.objects.create(
            departamento=tecnologia,
            nombre='Infraestructura',
        )

        response = self.client.post(
            '/api/perfiles-genericos/',
            {
                'nombre': 'Perfil Invalido',
                'usuario': 'perfil.invalido',
                'departamento': operaciones.pk,
                'subarea': infraestructura.pk,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('subarea', response.json())

    def test_admin_can_permanently_delete_perfil_generico(self):
        self.auth(self.admin)
        perfil = PerfilGenerico.objects.create(
            nombre='Perfil Histórico',
            usuario='perfil.historico',
            estado='ACTIVO',
            departamento=self.department,
        )

        response = self.client.delete(
            f'/api/perfiles-genericos/{perfil.pk}/'
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(PerfilGenerico.objects.filter(pk=perfil.pk).exists())

    def test_operator_can_deactivate_perfil_with_patch(self):
        self.auth(self.operator)
        perfil = PerfilGenerico.objects.create(
            nombre='Perfil Operador',
            usuario='perfil.operador',
            estado='ACTIVO',
            departamento=self.department,
        )

        response = self.client.patch(
            f'/api/perfiles-genericos/{perfil.pk}/',
            {'estado': 'INACTIVO'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        perfil.refresh_from_db()
        self.assertEqual(perfil.estado, 'INACTIVO')

    def test_perfiles_can_filter_by_department_and_subarea(self):
        self.auth(self.admin)
        tecnologia = Departamento.objects.create(nombre='Tecnología')
        operaciones = Departamento.objects.create(nombre='Operaciones')
        infraestructura = SubArea.objects.create(
            departamento=tecnologia,
            nombre='Infraestructura',
        )
        desarrollo = SubArea.objects.create(
            departamento=tecnologia,
            nombre='Desarrollo',
        )

        PerfilGenerico.objects.create(
            nombre='Infra',
            usuario='perfil.infra.filter',
            departamento=tecnologia,
            subarea=infraestructura,
        )
        PerfilGenerico.objects.create(
            nombre='Dev',
            usuario='perfil.dev.filter',
            departamento=tecnologia,
            subarea=desarrollo,
        )
        PerfilGenerico.objects.create(
            nombre='Ops',
            usuario='perfil.ops.filter',
            departamento=operaciones,
        )

        by_department = self.client.get(
            f'/api/perfiles-genericos/?departamento={tecnologia.pk}'
        )
        by_subarea = self.client.get(
            f'/api/perfiles-genericos/?subarea={infraestructura.pk}'
        )

        self.assertEqual(by_department.status_code, 200)
        self.assertEqual(by_department.json()['count'], 2)
        self.assertEqual(by_subarea.status_code, 200)
        self.assertEqual(by_subarea.json()['count'], 1)
        self.assertEqual(
            by_subarea.json()['results'][0]['usuario'],
            'perfil.infra.filter',
        )
    def test_cannot_delete_department_or_subarea_used_by_perfil(self):
        self.auth(self.admin)
        departamento = Departamento.objects.create(nombre='Tecnología')
        subarea = SubArea.objects.create(
            departamento=departamento,
            nombre='Infraestructura',
        )
        PerfilGenerico.objects.create(
            nombre='Perfil Relacionado',
            usuario='perfil.relacionado',
            departamento=departamento,
            subarea=subarea,
        )

        subarea_response = self.client.delete(
            f'/api/subareas/{subarea.pk}/'
        )
        departamento_response = self.client.delete(
            f'/api/departamentos/{departamento.pk}/'
        )

        self.assertEqual(subarea_response.status_code, 400)
        self.assertEqual(departamento_response.status_code, 400)
        self.assertTrue(SubArea.objects.filter(pk=subarea.pk).exists())
        self.assertTrue(Departamento.objects.filter(pk=departamento.pk).exists())



    def test_usuario_email_duplicate_is_case_insensitive(self):
        self.auth(self.admin)
        departamento = Departamento.objects.create(nombre='Tecnología')
        response = self.client.post(
            '/api/usuarios/',
            {
                'nombre_completo': 'Persona Correo',
                'usuario_red': 'pcorreo',
                'correo_corp': '  PUNO@EXAMPLE.COM  ',
                'departamento': departamento.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('correo_corp', response.json())

    def test_usuario_rejects_whitespace_in_network_user(self):
        self.auth(self.admin)
        departamento = Departamento.objects.create(nombre='Tecnología')
        response = self.client.post(
            '/api/usuarios/',
            {
                'nombre_completo': 'Persona Espacio',
                'usuario_red': 'usuario con espacio',
                'correo_corp': 'espacio@example.com',
                'departamento': departamento.pk,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('usuario_red', response.json())

    def test_usuario_hostname_is_valid_and_case_insensitive_unique(self):
        self.auth(self.admin)
        departamento = Departamento.objects.create(nombre='Tecnología')
        self.portal_user.departamento = departamento
        self.portal_user.hostname = 'CL-NB-001'
        self.portal_user.save()

        duplicate = self.client.post(
            '/api/usuarios/',
            {
                'nombre_completo': 'Persona Host',
                'usuario_red': 'phost',
                'correo_corp': 'phost@example.com',
                'departamento': departamento.pk,
                'hostname': 'cl-nb-001',
            },
            format='json',
        )
        invalid = self.client.post(
            '/api/usuarios/',
            {
                'nombre_completo': 'Persona Host Dos',
                'usuario_red': 'phost2',
                'correo_corp': 'phost2@example.com',
                'departamento': departamento.pk,
                'hostname': 'HOST INVALIDO',
            },
            format='json',
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertIn('hostname', duplicate.json())
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('hostname', invalid.json())

    def test_equipment_requires_brand_and_model(self):
        self.auth(self.operator)
        response = self.client.post(
            '/api/equipos/',
            {
                'tipo': 'Notebook',
                'marca': '   ',
                'modelo': '   ',
                'numero_serie': 'SER-REQ-1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertTrue('marca' in body or 'modelo' in body)

    def test_equipment_serial_duplicate_is_case_insensitive(self):
        self.auth(self.operator)
        Equipamiento.objects.create(
            tipo='Monitor',
            marca='Dell',
            modelo='P2422H',
            numero_serie='SERIE-CASE-01',
        )
        response = self.client.post(
            '/api/equipos/',
            {
                'tipo': 'Monitor',
                'marca': 'Dell',
                'modelo': 'P2422H',
                'numero_serie': 'serie-case-01',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('numero_serie', response.json())

    def test_pc_generico_rejects_duplicate_serial_and_asset(self):
        self.auth(self.operator)
        department = Departamento.objects.create(nombre='Soporte PCs')
        PCGenerico.objects.create(
            usuario_local='local1',
            hostname='PC-GEN-01',
            numero_serie='PCSER-01',
            activo_fijo='AFPC001',
            departamento=department,
        )

        duplicate_serial = self.client.post(
            '/api/pcs-genericos/',
            {
                'usuario_local': 'local2',
                'hostname': 'PC-GEN-02',
                'numero_serie': 'pcser-01',
                'departamento': department.pk,
            },
            format='json',
        )
        duplicate_asset = self.client.post(
            '/api/pcs-genericos/',
            {
                'usuario_local': 'local3',
                'hostname': 'PC-GEN-03',
                'activo_fijo': 'afpc001',
                'departamento': department.pk,
            },
            format='json',
        )

        self.assertEqual(duplicate_serial.status_code, 400)
        self.assertIn('numero_serie', duplicate_serial.json())
        self.assertEqual(duplicate_asset.status_code, 400)
        self.assertIn('activo_fijo', duplicate_asset.json())

    def test_anexo_rejects_non_numeric_number(self):
        self.auth(self.operator)
        response = self.client.post(
            '/api/anexos/',
            {'numero_anexo': '30A5'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('numero_anexo', response.json())

    def test_perfil_rejects_inactive_department_and_invalid_type(self):
        self.auth(self.operator)
        inactive = Departamento.objects.create(nombre='Inactivo', activo=False)
        active = Departamento.objects.create(nombre='Tecnología')

        blocked_department = self.client.post(
            '/api/perfiles-genericos/',
            {
                'nombre': 'Perfil Inactivo',
                'usuario': 'perfil.inactivo',
                'departamento': inactive.pk,
                'tipo': 'On Premise',
            },
            format='json',
        )
        invalid_type = self.client.post(
            '/api/perfiles-genericos/',
            {
                'nombre': 'Perfil Tipo',
                'usuario': 'perfil.tipo',
                'departamento': active.pk,
                'tipo': 'OTRO',
            },
            format='json',
        )

        self.assertEqual(blocked_department.status_code, 400)
        self.assertIn('departamento', blocked_department.json())
        self.assertEqual(invalid_type.status_code, 400)
        self.assertIn('tipo', invalid_type.json())

    def test_ip_assigned_to_user_cannot_set_other_assignment(self):
        self.auth(self.admin)
        ip = IP.objects.create(
            direccion_ip='172.23.1.80',
            usuario=self.portal_user,
        )
        response = self.client.patch(
            f'/api/ips/{ip.pk}/',
            {'asignado_otro': 'Impresora Piso 1'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('asignado_otro', response.json())
        ip.refresh_from_db()
        self.assertFalse(ip.asignado_otro)

    def test_servidor_rejects_invalid_hostname(self):
        self.auth(self.operator)
        ip = IP.objects.create(direccion_ip='172.23.1.90')
        response = self.client.post(
            '/api/servidores/',
            {
                'ip': ip.direccion_ip,
                'hostname': 'SERVIDOR INVALIDO',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('hostname', response.json())
        self.assertFalse(Servidor.objects.filter(ip=ip).exists())


class ServerIpIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user(
            'server-admin',
            password='StrongPass!123',
        )
        self.admin.groups.add(admin_group)
        self.client.force_authenticate(user=self.admin)
        self.department = Departamento.objects.create(nombre='Servidores')

        self.first_ip = IP.objects.create(direccion_ip='172.23.1.100')
        self.second_ip = IP.objects.create(direccion_ip='172.23.1.101')

    def test_server_assignment_change_and_delete_sync_ip_state(self):
        created = self.client.post(
            '/api/servidores/',
            {
                'ip': self.first_ip.direccion_ip,
                'hostname': 'SRV-APP-01',
                'descripcion': 'Aplicaciones',
            },
            format='json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['ip'], self.first_ip.direccion_ip)
        servidor_id = created.json()['id']

        self.first_ip.refresh_from_db()
        self.assertEqual(self.first_ip.estado, 'RESERVADA')
        self.assertEqual(self.first_ip.asignado_otro, 'Servidor: SRV-APP-01')

        changed = self.client.patch(
            f'/api/servidores/{servidor_id}/',
            {'ip': self.second_ip.direccion_ip},
            format='json',
        )
        self.assertEqual(changed.status_code, 200)

        self.first_ip.refresh_from_db()
        self.second_ip.refresh_from_db()
        self.assertEqual(self.first_ip.estado, 'LIBRE')
        self.assertIsNone(self.first_ip.asignado_otro)
        self.assertEqual(self.second_ip.estado, 'RESERVADA')

        blocked_delete = self.client.delete(f'/api/ips/{self.second_ip.pk}/')
        self.assertEqual(blocked_delete.status_code, 400)

        deleted = self.client.delete(f'/api/servidores/{servidor_id}/')
        self.assertEqual(deleted.status_code, 204)
        self.second_ip.refresh_from_db()
        self.assertEqual(self.second_ip.estado, 'LIBRE')
        self.assertIsNone(self.second_ip.asignado_otro)

    def test_server_rejects_reserved_or_wrong_segment_ip(self):
        reserved = IP.objects.create(
            direccion_ip='172.23.1.102',
            asignado_otro='Impresora',
        )
        wrong_segment = IP.objects.create(direccion_ip='172.24.1.100')

        reserved_response = self.client.post(
            '/api/servidores/',
            {'ip': reserved.direccion_ip, 'hostname': 'SRV-RES-01'},
            format='json',
        )
        wrong_response = self.client.post(
            '/api/servidores/',
            {'ip': wrong_segment.direccion_ip, 'hostname': 'SRV-WRONG-01'},
            format='json',
        )

        self.assertEqual(reserved_response.status_code, 400)
        self.assertIn('ip', reserved_response.json())
        self.assertEqual(wrong_response.status_code, 400)
        self.assertIn('ip', wrong_response.json())

    def test_notebook_ip_is_derived_from_assigned_user(self):
        user = Usuario.objects.create(
            nombre_completo='Usuario Notebook',
            usuario_red='unotebook',
            correo_corp='unotebook@example.com',
            departamento=self.department,
        )
        self.first_ip.usuario = user
        self.first_ip.save()
        notebook = Equipamiento.objects.create(
            usuario=user,
            tipo='Notebook',
            marca='Lenovo',
            modelo='T14',
            numero_serie='NB-IP-001',
        )

        first_result = self.client.get(f'/api/equipos/{notebook.pk}/')
        self.assertEqual(first_result.status_code, 200)
        self.assertEqual(first_result.json()['ip_asignada'], '172.23.1.100')

        self.first_ip.usuario = None
        self.first_ip.save()
        self.second_ip.usuario = user
        self.second_ip.save()

        second_result = self.client.get(f'/api/equipos/{notebook.pk}/')
        self.assertEqual(second_result.json()['ip_asignada'], '172.23.1.101')


class PCGenericoIpIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user(
            'pc-ip-admin',
            password='StrongPass!123',
        )
        self.admin.groups.add(admin_group)
        self.client.force_authenticate(user=self.admin)

        self.first_ip = IP.objects.create(direccion_ip='172.24.1.120')
        self.second_ip = IP.objects.create(direccion_ip='192.168.30.120')
        self.department = Departamento.objects.create(nombre='Infraestructura')

    def test_pc_assignment_change_release_and_delete_sync_ip_state(self):
        created = self.client.post(
            '/api/pcs-genericos/',
            {
                'usuario_local': 'soporte.local',
                'hostname': 'PC-GEN-IP-01',
                'ip_seleccionada': self.first_ip.direccion_ip,
                'departamento': self.department.pk,
            },
            format='json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['ip_actual'], self.first_ip.direccion_ip)
        pc_id = created.json()['id']

        self.first_ip.refresh_from_db()
        self.assertEqual(self.first_ip.estado, 'RESERVADA')
        self.assertEqual(
            self.first_ip.asignado_otro,
            'PC Genérico: PC-GEN-IP-01',
        )

        renamed = self.client.patch(
            f'/api/pcs-genericos/{pc_id}/',
            {'hostname': 'PC-GEN-IP-RENAMED'},
            format='json',
        )
        self.assertEqual(renamed.status_code, 200)
        self.first_ip.refresh_from_db()
        self.assertEqual(
            self.first_ip.asignado_otro,
            'PC Genérico: PC-GEN-IP-RENAMED',
        )

        changed = self.client.patch(
            f'/api/pcs-genericos/{pc_id}/',
            {'ip_seleccionada': self.second_ip.direccion_ip},
            format='json',
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()['ip_actual'], self.second_ip.direccion_ip)

        self.first_ip.refresh_from_db()
        self.second_ip.refresh_from_db()
        self.assertEqual(self.first_ip.estado, 'LIBRE')
        self.assertIsNone(self.first_ip.asignado_otro)
        self.assertEqual(self.second_ip.estado, 'RESERVADA')

        blocked_ip_edit = self.client.patch(
            f'/api/ips/{self.second_ip.pk}/',
            {'asignado_otro': 'Asignación manual'},
            format='json',
        )
        self.assertEqual(blocked_ip_edit.status_code, 400)

        released = self.client.patch(
            f'/api/pcs-genericos/{pc_id}/',
            {'ip_seleccionada': None},
            format='json',
        )
        self.assertEqual(released.status_code, 200)
        self.assertIsNone(released.json()['ip_actual'])
        self.second_ip.refresh_from_db()
        self.assertEqual(self.second_ip.estado, 'LIBRE')

        reassigned = self.client.patch(
            f'/api/pcs-genericos/{pc_id}/',
            {'ip_seleccionada': self.first_ip.direccion_ip},
            format='json',
        )
        self.assertEqual(reassigned.status_code, 200)
        deleted = self.client.delete(f'/api/pcs-genericos/{pc_id}/')
        self.assertEqual(deleted.status_code, 204)
        self.first_ip.refresh_from_db()
        self.assertEqual(self.first_ip.estado, 'LIBRE')
        self.assertIsNone(self.first_ip.asignado_otro)

    def test_pc_rejects_ip_reserved_by_another_owner(self):
        reserved = IP.objects.create(
            direccion_ip='172.25.1.120',
            asignado_otro='Impresora',
        )
        user = Usuario.objects.create(
            nombre_completo='Usuario con IP',
            usuario_red='usuario.ip.pc',
            correo_corp='usuario.ip.pc@example.com',
            departamento=self.department,
        )
        user_ip = IP.objects.create(
            direccion_ip='192.168.20.120',
            usuario=user,
        )

        for index, address in enumerate(
            (reserved.direccion_ip, user_ip.direccion_ip),
            start=1,
        ):
            response = self.client.post(
                '/api/pcs-genericos/',
                {
                    'usuario_local': f'local{index}',
                    'hostname': f'PC-CONFLICT-{index}',
                    'ip_seleccionada': address,
                    'departamento': self.department.pk,
                },
                format='json',
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn('ip_seleccionada', response.json())


@override_settings(PORTAL_IDLE_TIMEOUT_SECONDS=300)
class PortalSessionTests(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.user = User.objects.create_user(
            'session-admin',
            password='StrongPass!123',
        )
        self.user.groups.add(admin_group)
        self.client = APIClient()

    def login(self):
        return self.client.post(
            '/api/auth/login/',
            {'username': 'session-admin', 'password': 'StrongPass!123'},
            format='json',
        )

    def test_login_creates_unique_tokenized_session(self):
        first = self.login()
        self.assertEqual(first.status_code, 200)
        first_token = AccessToken(first.json()['access'])
        first_sid = first_token['sid']
        self.assertTrue(PortalSession.objects.filter(pk=first_sid).exists())

        second_client = APIClient()
        second = second_client.post(
            '/api/auth/login/',
            {'username': 'session-admin', 'password': 'StrongPass!123'},
            format='json',
        )
        second_sid = AccessToken(second.json()['access'])['sid']
        self.assertNotEqual(first_sid, second_sid)

    def test_refresh_restores_active_session_and_activity_touches_it(self):
        login = self.login()
        token = login.json()['access']
        sid = AccessToken(token)['sid']
        portal_session = PortalSession.objects.get(pk=sid)
        previous_activity = portal_session.last_activity

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        activity = self.client.post('/api/auth/activity/')
        self.assertEqual(activity.status_code, 204)
        portal_session.refresh_from_db()
        self.assertGreaterEqual(portal_session.last_activity, previous_activity)

        self.client.credentials()
        refreshed = self.client.post(
            '/api/auth/refresh/',
            HTTP_X_PORTAL_ACTIVITY='1',
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(AccessToken(refreshed.json()['access'])['sid'], str(sid))

    def test_refresh_rejects_session_after_effective_inactivity(self):
        login = self.login()
        sid = AccessToken(login.json()['access'])['sid']
        PortalSession.objects.filter(pk=sid).update(
            last_activity=timezone.now() - timedelta(minutes=6)
        )

        refreshed = self.client.post(
            '/api/auth/refresh/',
            HTTP_X_PORTAL_ACTIVITY='1',
        )
        self.assertEqual(refreshed.status_code, 401)
        self.assertIsNotNone(PortalSession.objects.get(pk=sid).revoked_at)

    def test_unexpected_refresh_error_is_not_reported_as_expired_session(self):
        self.login()

        with patch(
            'core.auth_views.get_active_portal_session',
            side_effect=RuntimeError('fallo interno de prueba'),
        ), self.assertLogs('core.auth_views', level='ERROR') as captured:
            refreshed = self.client.post('/api/auth/refresh/')

        self.assertEqual(refreshed.status_code, 503)
        self.assertEqual(
            refreshed.json()['detail'],
            'No fue posible renovar la sesión.',
        )
        self.assertTrue(
            any('session_refresh_unexpected_error' in line for line in captured.output)
        )


class CsrfSessionProtectionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.user = User.objects.create_user(
            'csrf-admin',
            password='StrongPass!123',
        )
        self.user.groups.add(admin_group)
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf_token(self):
        response = self.client.get('/api/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', response.cookies)
        self.assertRegex(response['X-Request-ID'], r'^[0-9a-f]{32}$')
        return response.json()['csrfToken']

    def credentials(self):
        return {'username': 'csrf-admin', 'password': 'StrongPass!123'}

    def test_login_requires_csrf_token(self):
        rejected = self.client.post(
            '/api/auth/login/',
            self.credentials(),
            format='json',
        )
        self.assertEqual(rejected.status_code, 403)

        csrf_token = self.csrf_token()
        accepted = self.client.post(
            '/api/auth/login/',
            self.credentials(),
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(accepted.status_code, 200)

    def test_refresh_and_logout_require_csrf_token(self):
        csrf_token = self.csrf_token()
        login = self.client.post(
            '/api/auth/login/',
            self.credentials(),
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login.status_code, 200)

        rejected_refresh = self.client.post('/api/auth/refresh/')
        self.assertEqual(rejected_refresh.status_code, 403)

        refreshed = self.client.post(
            '/api/auth/refresh/',
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(refreshed.status_code, 200)

        rejected_logout = self.client.post('/api/auth/logout/')
        self.assertEqual(rejected_logout.status_code, 403)

        logged_out = self.client.post(
            '/api/auth/logout/',
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(logged_out.status_code, 204)


class PerformanceQueryTests(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        self.admin = User.objects.create_user(
            'performance-admin',
            password='StrongPass!123',
        )
        self.admin.groups.add(admin_group)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.department = Departamento.objects.create(nombre='Rendimiento')
        for index in range(5):
            user = Usuario.objects.create(
                nombre_completo=f'Persona Rendimiento {index}',
                usuario_red=f'perf{index}',
                correo_corp=f'perf{index}@example.com',
                departamento=self.department,
            )
            IP.objects.create(
                direccion_ip=f'172.23.1.{150 + index}',
                usuario=user,
            )
            Equipamiento.objects.create(
                usuario=user,
                tipo='Notebook',
                marca='Lenovo',
                modelo='T14',
                numero_serie=f'PERF-{index}',
            )
            Anexo.objects.create(
                numero_anexo=f'8{index:03d}',
                usuario=user,
            )

    def test_list_endpoints_do_not_scale_queries_per_row(self):
        with CaptureQueriesContext(connection) as user_queries:
            users = self.client.get('/api/usuarios/')
            users.content
        with CaptureQueriesContext(connection) as equipment_queries:
            equipment = self.client.get('/api/equipos/')
            equipment.content
        with CaptureQueriesContext(connection) as extension_queries:
            extensions = self.client.get('/api/anexos/')
            extensions.content

        self.assertEqual(users.status_code, 200)
        self.assertLessEqual(len(user_queries), 4)
        self.assertLessEqual(len(equipment_queries), 3)
        self.assertLessEqual(len(extension_queries), 3)
        self.assertNotIn('historial', users.json()['results'][0])
        self.assertNotIn('historial', equipment.json()['results'][0])
        self.assertNotIn('historial', extensions.json()['results'][0])

    def test_large_lists_return_page_metadata(self):
        response = self.client.get('/api/usuarios/?page=2&page_size=2')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['count'], 5)
        self.assertEqual(payload['page'], 2)
        self.assertEqual(payload['page_size'], 2)
        self.assertEqual(payload['total_pages'], 3)
        self.assertEqual(len(payload['results']), 2)

    def test_ip_segment_stats_avoid_loading_full_ip_rows(self):
        response = self.client.get('/api/reference-data/?include=ips_stats')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), {'ips_stats'})
        self.assertEqual(payload['ips_stats']['172.23']['total'], 5)
        self.assertEqual(payload['ips_stats']['172.23']['reservadas'], 5)

    def test_user_stats_are_aggregated_by_department(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(
                '/api/reference-data/?include=usuarios_stats'
            )
            response.content

        self.assertEqual(response.status_code, 200)
        # Una consulta valida el rol y otra calcula todos los conteos.
        self.assertLessEqual(len(queries), 2)
        payload = response.json()
        self.assertEqual(set(payload), {'usuarios_stats'})
        self.assertEqual(payload['usuarios_stats']['total'], 5)
        self.assertEqual(
            payload['usuarios_stats']['departamentos'],
            [{'nombre': 'Rendimiento', 'total': 5}],
        )

    def test_ip_segment_filter_orders_hosts_numerically(self):
        for host in (10, 2, 1):
            IP.objects.create(direccion_ip=f'172.24.1.{host}')

        response = self.client.get(
            '/api/ips/',
            {'segmento': '172.24', 'page_size': 200},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['direccion_ip'] for item in response.json()['results']],
            ['172.24.1.1', '172.24.1.2', '172.24.1.10'],
        )

    def test_equipment_category_filter_is_applied_by_backend(self):
        peripheral = Equipamiento.objects.create(
            tipo='Monitor',
            marca='Dell',
            modelo='P2422H',
            numero_serie='PERIPHERAL-1',
        )
        Equipamiento.objects.create(
            tipo='Celular',
            marca='Samsung',
            modelo='A55',
            numero_serie='PHONE-1',
        )

        response = self.client.get(
            '/api/equipos/',
            {'categoria': 'PERIFERICOS', 'page_size': 200},
        )

        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual([item['id'] for item in results], [peripheral.id])
        self.assertEqual(results[0]['tipo'], 'Monitor')

    def test_history_is_loaded_only_on_detail(self):
        user = Usuario.objects.get(usuario_red='perf0')
        response = self.client.get(f'/api/usuarios/{user.pk}/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('historial', response.json())
        self.assertIn('equipos', response.json())

    def test_reference_endpoint_returns_lightweight_sections(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/api/reference-data/')
            response.content

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 6)
        self.assertEqual(
            set(response.json()),
            {'usuarios', 'ips', 'departamentos', 'perfiles'},
        )
        self.assertNotIn('correo_corp', response.json()['usuarios'][0])

    def test_user_department_filter_uses_current_department_relation(self):
        technology = Departamento.objects.create(nombre='TECNOLOGÍA')
        technology_user = Usuario.objects.create(
            nombre_completo='Persona Tecnología',
            usuario_red='tecnologia-test',
            correo_corp='tecnologia@example.com',
            departamento=technology,
        )
        Usuario.objects.filter(pk=technology_user.pk).update(dpto_area='TI')

        response = self.client.get(
            '/api/usuarios/',
            {'dpto_area': 'TECNOLOGÍA'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item['id'] for item in response.json()['results']],
            [technology_user.id],
        )
