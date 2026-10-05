from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.models import Departamento, SubArea, Usuario


class ValidatePortalIntegrityCommandTests(TestCase):
    def setUp(self):
        self.department = Departamento.objects.create(nombre='Tecnología')
        self.user = Usuario.objects.create(
            nombre_completo='Persona Integridad',
            usuario_red='integridad',
            correo_corp='integridad@example.com',
            departamento=self.department,
        )

    def test_valid_data_passes(self):
        output = StringIO()

        call_command('validar_integridad_portal', stdout=output)

        self.assertIn('Integridad confirmada', output.getvalue())

    def test_cross_department_subarea_fails(self):
        other_department = Departamento.objects.create(nombre='Operaciones')
        other_subarea = SubArea.objects.create(
            departamento=other_department,
            nombre='Soporte',
        )
        Usuario.objects.filter(pk=self.user.pk).update(subarea=other_subarea)
        output = StringIO()

        with self.assertRaises(CommandError):
            call_command(
                'validar_integridad_portal',
                muestras=2,
                stdout=output,
                stderr=StringIO(),
            )

        self.assertIn('usuario_subarea_departamento', output.getvalue())
