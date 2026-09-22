from django.contrib.auth.models import User, Group
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from cryptography.fernet import Fernet
from core.models import Usuario, PerfilGenerico, IP, Equipamiento, Anexo, SecurityAuditLog, Departamento, SubArea, PCGenerico, Servidor

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

    def test_perfil_generico_delete_is_soft_deactivation(self):
        self.auth(self.admin)
        perfil = PerfilGenerico.objects.create(
            nombre='Perfil Histórico',
            usuario='perfil.historico',
            estado='ACTIVO',
        )

        response = self.client.delete(
            f'/api/perfiles-genericos/{perfil.pk}/'
        )

        self.assertEqual(response.status_code, 204)
        self.assertTrue(PerfilGenerico.objects.filter(pk=perfil.pk).exists())
        perfil.refresh_from_db()
        self.assertEqual(perfil.estado, 'INACTIVO')

    def test_operator_can_deactivate_perfil_with_patch(self):
        self.auth(self.operator)
        perfil = PerfilGenerico.objects.create(
            nombre='Perfil Operador',
            usuario='perfil.operador',
            estado='ACTIVO',
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
        self.assertEqual(len(by_department.json()), 2)
        self.assertEqual(by_subarea.status_code, 200)
        self.assertEqual(len(by_subarea.json()), 1)
        self.assertEqual(by_subarea.json()[0]['usuario'], 'perfil.infra.filter')
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
        PCGenerico.objects.create(
            usuario_local='local1',
            hostname='PC-GEN-01',
            numero_serie='PCSER-01',
            activo_fijo='AFPC001',
        )

        duplicate_serial = self.client.post(
            '/api/pcs-genericos/',
            {
                'usuario_local': 'local2',
                'hostname': 'PC-GEN-02',
                'numero_serie': 'pcser-01',
            },
            format='json',
        )
        duplicate_asset = self.client.post(
            '/api/pcs-genericos/',
            {
                'usuario_local': 'local3',
                'hostname': 'PC-GEN-03',
                'activo_fijo': 'afpc001',
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
        response = self.client.post(
            '/api/servidores/',
            {
                'ip': '172.23.50.10',
                'hostname': 'SERVIDOR INVALIDO',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('hostname', response.json())
        self.assertFalse(Servidor.objects.filter(ip='172.23.50.10').exists())
