from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from core.models import Departamento, Usuario


class HostnameReportTests(TestCase):
    def test_report_lists_only_normalized_duplicate_hostnames(self):
        department = Departamento.objects.create(nombre='Reporte Hostnames')
        for index, hostname in enumerate(('CL-DUP-01', 'cl-dup-01', 'CL-UNICO')):
            Usuario.objects.create(
                nombre_completo=f'Persona Reporte {index}',
                usuario_red=f'reporte{index}',
                correo_corp=f'reporte{index}@example.com',
                departamento=department,
                hostname=hostname,
            )

        with TemporaryDirectory() as folder:
            output = Path(folder) / 'reporte.txt'
            call_command(
                'reportar_hostnames_usuarios',
                output=output,
                verbosity=0,
            )
            report = output.read_text(encoding='utf-8-sig')

        self.assertIn('Grupos duplicados: 1', report)
        self.assertIn('Usuarios involucrados: 2', report)
        self.assertIn('CL-DUP-01', report)
        self.assertIn('cl-dup-01', report)
        self.assertNotIn('CL-UNICO', report)
