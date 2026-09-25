from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Departamento, PCGenerico, PerfilGenerico, Usuario
from core.serializers import (
    PCGenericoSerializer,
    PerfilGenericoSerializer,
    UsuarioSerializer,
)


class RequiredDepartmentTests(TestCase):
    def setUp(self):
        self.department = Departamento.objects.create(nombre='Área Obligatoria')
        self.user = Usuario.objects.create(
            nombre_completo='Persona con Área',
            usuario_red='persona.area',
            correo_corp='persona.area@example.com',
            departamento=self.department,
        )
        self.profile = PerfilGenerico.objects.create(
            nombre='Perfil con Área',
            usuario='perfil.area',
            departamento=self.department,
        )
        self.pc = PCGenerico.objects.create(
            usuario_local='local.area',
            hostname='PC-AREA-01',
            departamento=self.department,
        )

    def assert_database_rejects_department_removal(self, model, pk):
        with self.assertRaises(IntegrityError), transaction.atomic():
            model.objects.filter(pk=pk).update(departamento=None)

    def test_database_rejects_removing_required_departments(self):
        self.assert_database_rejects_department_removal(Usuario, self.user.pk)
        self.assert_database_rejects_department_removal(
            PerfilGenerico,
            self.profile.pk,
        )
        self.assert_database_rejects_department_removal(PCGenerico, self.pc.pk)

    def test_api_serializers_return_clear_department_errors(self):
        serializers = (
            UsuarioSerializer(
                self.user,
                data={'departamento': None},
                partial=True,
            ),
            PerfilGenericoSerializer(
                self.profile,
                data={'departamento': None},
                partial=True,
            ),
            PCGenericoSerializer(
                self.pc,
                data={'departamento': None},
                partial=True,
            ),
        )

        for serializer in serializers:
            self.assertFalse(serializer.is_valid())
            self.assertIn('departamento', serializer.errors)
