from django.contrib import admin

from .models import (
    AsignacionIP,
    Departamento,
    HistorialAsignacionIP,
    HistorialServidor,
    HistorialPerfilGenerico,
    SubArea,
)


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


@admin.register(AsignacionIP)
class AsignacionIPAdmin(admin.ModelAdmin):
    list_display = (
        'ip',
        'tipo',
        'propietario_nombre',
        'fecha_actualizacion',
    )
    list_filter = ('tipo',)
    search_fields = (
        'ip__direccion_ip',
        'usuario__nombre_completo',
        'servidor__hostname',
        'pc_generico__hostname',
        'detalle',
    )
    readonly_fields = ('fecha_asignacion', 'fecha_actualizacion')


@admin.register(HistorialAsignacionIP)
class HistorialAsignacionIPAdmin(admin.ModelAdmin):
    list_display = (
        'direccion_ip',
        'accion',
        'tipo',
        'propietario_nombre',
        'realizado_por',
        'fecha_movimiento',
    )
    list_filter = ('accion', 'tipo')
    search_fields = ('direccion_ip', 'propietario_nombre', 'realizado_por')
    readonly_fields = (
        'ip',
        'direccion_ip',
        'accion',
        'tipo',
        'propietario_id',
        'propietario_nombre',
        'realizado_por',
        'fecha_movimiento',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistorialServidor)
class HistorialServidorAdmin(admin.ModelAdmin):
    list_display = (
        'servidor_hostname',
        'accion',
        'modificado_por',
        'fecha_movimiento',
    )
    list_filter = ('accion',)
    search_fields = ('servidor_hostname', 'modificado_por', 'observacion')
    readonly_fields = (
        'servidor',
        'servidor_hostname',
        'accion',
        'modificado_por',
        'observacion',
        'fecha_movimiento',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistorialPerfilGenerico)
class HistorialPerfilGenericoAdmin(admin.ModelAdmin):
    list_display = (
        'perfil_nombre',
        'perfil_usuario',
        'accion',
        'modificado_por',
        'fecha_movimiento',
    )
    list_filter = ('accion',)
    search_fields = (
        'perfil_nombre',
        'perfil_usuario',
        'modificado_por',
        'observacion',
    )
    readonly_fields = (
        'perfil',
        'perfil_nombre',
        'perfil_usuario',
        'accion',
        'modificado_por',
        'observacion',
        'fecha_movimiento',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
