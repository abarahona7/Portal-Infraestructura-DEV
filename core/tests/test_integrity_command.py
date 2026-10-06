from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.models import Departamento, Equipamiento, SubArea, Usuario


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

    def test_mobile_line_assigned_to_two_users_is_reported_without_modifying_data(self):
        second = Usuario.objects.create(
            nombre_completo='Otra Persona Integridad',
            usuario_red='integridad.dos',
            correo_corp='integridad.dos@example.com',
            departamento=self.department,
        )
        first_equipment = Equipamiento.objects.create(
            usuario=self.user, tipo='Celular', marca='Apple', modelo='iPhone',
            numero_telefono='+56912345678',
        )
        second_equipment = Equipamiento.objects.create(
            usuario=second, tipo='Celular', marca='Samsung', modelo='Galaxy',
            numero_telefono='+56912345678',
        )
        output = StringIO()

        with self.assertRaises(CommandError):
            call_command('validar_integridad_portal', stdout=output, stderr=StringIO())

        self.assertIn('equipo_linea_otro_usuario', output.getvalue())
        self.assertIn(str(first_equipment.pk), output.getvalue())
        self.assertIn(str(second_equipment.pk), output.getvalue())
        first_equipment.refresh_from_db()
        second_equipment.refresh_from_db()
        self.assertEqual(first_equipment.numero_telefono, second_equipment.numero_telefono)
