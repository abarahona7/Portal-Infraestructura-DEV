"""Regresiones A05/A10 con payloads sintéticos e inofensivos."""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth.models import Group, User
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Departamento, Equipamiento, Usuario
from core.services.acta_entrega_pdf import generar_acta_entrega_pdf


class OutboundClientGuardTests(SimpleTestCase):
    """Obliga a revisar cualquier cliente de red nuevo en el runtime del portal."""

    def test_runtime_no_incorpora_clientes_salientes_sin_control_centralizado(self):
        project_root = Path(__file__).resolve().parents[2]
        forbidden_imports = {'requests', 'httpx', 'aiohttp', 'socket'}
        findings = []

        for package in ('core', 'config'):
            for path in (project_root / package).rglob('*.py'):
                relative = path.relative_to(project_root)
                if 'tests' in relative.parts or 'migrations' in relative.parts:
                    continue
                tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(relative))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.split('.')[0] in forbidden_imports:
                                findings.append(f'{relative}:{node.lineno}:{alias.name}')
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        if module.split('.')[0] in forbidden_imports:
                            findings.append(f'{relative}:{node.lineno}:{module}')
                        if module == 'urllib' and any(
                            alias.name == 'request' for alias in node.names
                        ):
                            findings.append(f'{relative}:{node.lineno}:urllib.request')

        self.assertEqual(
            findings,
            [],
            'Todo cliente saliente nuevo debe pasar por una función segura y una revisión SSRF.',
        )


class PdfInjectionTests(SimpleTestCase):
    def test_acta_trata_como_texto_las_etiquetas_con_destinos_ssrf(self):
        destinations = (
            'http://127.0.0.1:9/probe.png',
            'http://169.254.169.254/latest/meta-data/probe.png',
            'http://rebind.invalid/probe.png',
        )
        for destination in destinations:
            with self.subTest(destination=destination):
                payload = f'<img src="{destination}"/>'
                usuario = SimpleNamespace(
                    nombre_completo=payload,
                    dpto_area=payload,
                    equipos=[SimpleNamespace(
                        tipo='Notebook', marca=payload, modelo='QA',
                        numero_serie=payload, af=None, accesorios=payload,
                        estado='ASIGNADO',
                    )],
                )
                with patch('reportlab.lib.utils.open_for_read') as opener:
                    pdf = generar_acta_entrega_pdf(usuario).getvalue()
                self.assertTrue(pdf.startswith(b'%PDF'))
                opened_sources = [str(call.args[0]) for call in opener.call_args_list]
                self.assertNotIn(destination, opened_sources)
                self.assertTrue(all(source.endswith('.png') for source in opened_sources))


@override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
class ApiInjectionTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name='Operador Infraestructura')
        self.operator = User.objects.create_user('a05-operator', password='StrongPass!123')
        self.operator.groups.add(group)
        self.client = APIClient()
        self.client.force_authenticate(user=self.operator)
        self.department = Departamento.objects.create(nombre='SEGURIDAD A05')
        self.person = Usuario.objects.create(
            nombre_completo='PERSONA A05', usuario_red='persona.a05',
            correo_corp='persona.a05@example.com', departamento=self.department,
        )
        Equipamiento.objects.create(
            tipo='Notebook', marca='Marca QA', modelo='Modelo QA',
            numero_serie='A05-SERIE-1', estado='STOCK',
        )

    def test_busqueda_sql_sintetica_permanece_como_parametro(self):
        before = Equipamiento.objects.count()
        for payload in ("' UNION SELECT 1--", "%' OR 1=1--"):
            response = self.client.get('/api/equipos/', {'search': payload})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['count'], 0)
        self.assertEqual(Equipamiento.objects.count(), before)

    def test_lookup_de_relacion_no_se_interpreta_como_filtro(self):
        response = self.client.get(
            '/api/equipos/',
            {'usuario__password__contains': 'irrelevante'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertNotIn('irrelevante', str(response.data))

    def test_rechaza_control_nulo_en_texto_persistente(self):
        response = self.client.post('/api/equipos/', {
            'tipo': 'Notebook', 'marca': 'MARCA\u0000OCULTA',
            'modelo': 'MODELO', 'estado': 'STOCK',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Equipamiento.objects.filter(marca__contains='OCULTA').exists())

    def test_rechaza_secreto_que_no_cabria_despues_del_cifrado(self):
        response = self.client.patch(
            f'/api/usuarios/{self.person.pk}/',
            {'password_gmail': 'á' * 128},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('password_gmail', response.data)
        self.person.refresh_from_db()
        self.assertFalse(self.person.password_gmail)

    def test_rechaza_prefijo_criptografico_reservado_en_secreto(self):
        response = self.client.patch(
            f'/api/usuarios/{self.person.pk}/',
            {'password_gmail': 'ENC2::contenido-no-cifrado'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('password_gmail', response.data)
        self.person.refresh_from_db()
        self.assertFalse(self.person.password_gmail)

    def test_nombre_pdf_no_permite_romper_content_disposition(self):
        self.person.usuario_red = 'persona";malicioso'
        self.person.save(update_fields=['usuario_red'])
        Equipamiento.objects.create(
            usuario=self.person, tipo='Celular', marca='QA', modelo='QA',
            numero_serie='A05-SERIE-2', estado='ASIGNADO',
        )
        response = self.client.get(f'/api/usuarios/{self.person.pk}/acta-entrega/')
        self.assertEqual(response.status_code, 200)
        header = response['Content-Disposition']
        self.assertNotIn('\r', header)
        self.assertNotIn('\n', header)
        self.assertNotIn('filename="Acta_Entrega_persona";malicioso.pdf"', header)
