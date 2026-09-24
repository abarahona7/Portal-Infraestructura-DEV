from django.test import TestCase

from core.models import Departamento, PCGenerico, SubArea
from core.serializers import PCGenericoListSerializer, PCGenericoSerializer


class PCGenericoDepartmentRelationTests(TestCase):
    def setUp(self):
        self.department = Departamento.objects.create(nombre='Tecnología')
        self.subarea = SubArea.objects.create(
            departamento=self.department,
            nombre='Soporte',
        )
        self.other_department = Departamento.objects.create(nombre='Finanzas')
        self.other_subarea = SubArea.objects.create(
            departamento=self.other_department,
            nombre='Tesorería',
        )

    def test_create_requires_department_and_synchronizes_legacy_value(self):
        missing_department = PCGenericoSerializer(data={
            'usuario_local': 'pc.local.sin.area',
            'hostname': 'PC-SIN-AREA',
        })
        self.assertFalse(missing_department.is_valid())
        self.assertIn('departamento', missing_department.errors)

        serializer = PCGenericoSerializer(data={
            'usuario_local': 'pc.local.soporte',
            'hostname': 'PC-SOPORTE-01',
            'departamento': self.department.pk,
            'subarea': self.subarea.pk,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        pc = serializer.save()

        self.assertEqual(pc.departamento_id, self.department.pk)
        self.assertEqual(pc.subarea_id, self.subarea.pk)
        self.assertEqual(pc.dpto_area, self.subarea.nombre)

        listed = PCGenericoListSerializer(
            PCGenerico.objects.select_related(
                'departamento',
                'subarea',
            ).get(pk=pc.pk)
        ).data
        self.assertEqual(listed['departamento_nombre'], 'Tecnología')
        self.assertEqual(listed['subarea_nombre'], 'Soporte')

    def test_rejects_subarea_from_another_department(self):
        serializer = PCGenericoSerializer(data={
            'usuario_local': 'pc.local.invalido',
            'hostname': 'PC-AREA-INVALIDA',
            'departamento': self.department.pk,
            'subarea': self.other_subarea.pk,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('subarea', serializer.errors)

    def test_rejects_new_inactive_department(self):
        self.other_department.activo = False
        self.other_department.save()
        serializer = PCGenericoSerializer(data={
            'usuario_local': 'pc.local.inactivo',
            'hostname': 'PC-AREA-INACTIVA',
            'departamento': self.other_department.pk,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('departamento', serializer.errors)

    def test_legacy_text_is_linked_when_model_is_used_directly(self):
        pc = PCGenerico.objects.create(
            usuario_local='pc.local.legado',
            hostname='PC-LEGADO-01',
            dpto_area='  TECNOLOGÍA  ',
        )

        self.assertEqual(pc.departamento_id, self.department.pk)
        self.assertEqual(pc.dpto_area, self.department.nombre)
