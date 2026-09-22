from django.contrib import admin

from .models import Departamento, SubArea


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'fecha_actualizacion')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(SubArea)
class SubAreaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'departamento', 'activo', 'fecha_actualizacion')
    list_filter = ('activo', 'departamento')
    search_fields = ('nombre', 'departamento__nombre')
    ordering = ('departamento__nombre', 'nombre')
