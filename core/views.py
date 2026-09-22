from django.http import HttpResponse
from rest_framework.decorators import action

from .services.acta_entrega_pdf import (
    generar_acta_entrega_pdf
)

from rest_framework import viewsets, filters, serializers
from .permissions import PortalRolePermission
from django_filters.rest_framework import (
    DjangoFilterBackend
)

from .models import (
    Usuario,
    Equipamiento,
    PerfilGenerico,
    IP,
    Anexo,
    PCGenerico,
    Servidor,
    Departamento,
    SubArea,
)

from .serializers import (
    UsuarioSerializer,
    EquipamientoSerializer,
    PerfilGenericoSerializer,
    IPSerializer,
    AnexoSerializer,
    PCGenericoSerializer,
    ServidorSerializer,
    DepartamentoSerializer,
    SubAreaSerializer,
)

from .audit import (
    set_current_audit_user,
    reset_current_audit_user,
)

class AuditUserMixin:
    def perform_create(self, serializer):
        token = set_current_audit_user(
            self.request.user
        )

        try:
            serializer.save()
        finally:
            reset_current_audit_user(token)

    def perform_update(self, serializer):
        token = set_current_audit_user(
            self.request.user
        )

        try:
            serializer.save()
        finally:
            reset_current_audit_user(token)

    def perform_destroy(self, instance):
        token = set_current_audit_user(
            self.request.user
        )

        try:
            instance.delete()
        finally:
            reset_current_audit_user(token)



class DepartamentoViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    permission_classes = [PortalRolePermission]
    queryset = Departamento.objects.prefetch_related('subareas').all()
    serializer_class = DepartamentoSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
    ]
    filterset_fields = ['activo']
    search_fields = ['nombre', 'subareas__nombre']

    def perform_destroy(self, instance):
        if instance.usuarios.exists() or instance.perfiles_genericos.exists():
            raise serializers.ValidationError({
                'detail': (
                    'No se puede eliminar este departamento porque tiene '
                    'usuarios o perfiles genéricos asociados. Puedes desactivarlo.'
                )
            })

        if instance.subareas.exists():
            raise serializers.ValidationError({
                'detail': (
                    'No se puede eliminar este departamento mientras tenga '
                    'subáreas registradas. Elimina primero las subáreas que no '
                    'estén en uso o desactiva el departamento.'
                )
            })

        super().perform_destroy(instance)


class SubAreaViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    permission_classes = [PortalRolePermission]
    queryset = SubArea.objects.select_related('departamento').all()
    serializer_class = SubAreaSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
    ]
    filterset_fields = ['departamento', 'activo']
    search_fields = ['nombre', 'departamento__nombre']

    def perform_destroy(self, instance):
        if instance.usuarios.exists() or instance.perfiles_genericos.exists():
            raise serializers.ValidationError({
                'detail': (
                    'No se puede eliminar esta subárea porque tiene usuarios '
                    'o perfiles genéricos asociados. Puedes desactivarla para '
                    'conservar las relaciones existentes.'
                )
            })

        super().perform_destroy(instance)


class IPViewSet(viewsets.ModelViewSet):
    permission_classes = [PortalRolePermission]
    queryset = IP.objects.all()
    serializer_class = IPSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]
    filterset_fields = ['estado']
    search_fields = [
        'direccion_ip',
        'observacion',
        'usuario__nombre_completo',
        'asignado_otro'
    ]

    def perform_destroy(self, instance):
        if instance.usuario_id:
            raise serializers.ValidationError({
                'detail': (
                    'No se puede eliminar una IP asignada a un usuario. '
                    'Libérala primero desde la ficha del usuario.'
                )
            })

        instance.delete()


# =========================================
# SERVIDORES
# =========================================

class ServidorViewSet(viewsets.ModelViewSet):
    permission_classes = [PortalRolePermission]
    queryset = Servidor.objects.all()
    serializer_class = ServidorSerializer

    filter_backends = [
        filters.SearchFilter
    ]

    search_fields = [
        'ip',
        'hostname',
        'descripcion',
    ]

class AnexoViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    # Único módulo visible para el rol Visualizador.
    # El permiso backend mantiene este acceso estrictamente de solo lectura.
    viewer_read_only = True
    permission_classes = [PortalRolePermission]
    queryset = Anexo.objects.select_related(
        'usuario'
    ).all()

    serializer_class = AnexoSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]

    filterset_fields = [
        'estado'
    ]

    search_fields = [
        'numero_anexo',
        'exterior',
        'observaciones',
        'usuario__nombre_completo',
        'usuario__dpto_area',
        'usuario__departamento__nombre',
        'usuario__subarea__nombre',
        'usuario__cargo',
        'usuario__correo_corp',
    ]


class UsuarioViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    permission_classes = [PortalRolePermission]
    queryset = Usuario.objects.select_related(
        'departamento',
        'subarea',
    ).all()
    serializer_class = UsuarioSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]

    filterset_fields = [
        'dpto_area',
        'departamento',
        'subarea',
        'estado'
    ]

    search_fields = [
        'nombre_completo',
        'usuario_red',
        'correo_corp',
        'hostname',
        'departamento__nombre',
        'subarea__nombre',
        'ip__direccion_ip'
    ]

    @action(
        detail=True,
        methods=['get'],
        url_path='acta-entrega'
    )
    def acta_entrega(self, request, pk=None):
        usuario = self.get_object()

        # Nombre de la persona logueada
        entregado_por = ""

        if request.user and request.user.is_authenticated:
            try:
                nombre_completo = (
                    request.user
                    .get_full_name()
                    .strip()
                )
            except (AttributeError, TypeError):
                nombre_completo = ""

            entregado_por = (
                nombre_completo
                or getattr(
                    request.user,
                    'username',
                    ''
                )
                or str(request.user)
            )

        pdf_buffer = generar_acta_entrega_pdf(
            usuario=usuario,
            entregado_por=entregado_por,
        )

        identificador = getattr(
            usuario,
            'usuario_red',
            None
        ) or usuario.pk

        nombre_archivo = (
            f"Acta_Entrega_{identificador}.pdf"
        )

        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf',
        )

        response['Content-Disposition'] = (
            f'inline; filename="{nombre_archivo}"'
        )

        return response


class EquipamientoViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    permission_classes = [PortalRolePermission]
    queryset = Equipamiento.objects.all()
    serializer_class = EquipamientoSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]

    filterset_fields = [
        'tipo',
        'estado'
    ]

    search_fields = [
        'marca',
        'modelo',
        'numero_serie',
        'hostname',
        'af',
        'usuario__nombre_completo',
        'usuario__usuario_red'
    ]


class PerfilGenericoViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    permission_classes = [PortalRolePermission]
    queryset = PerfilGenerico.objects.select_related(
        'departamento',
        'subarea',
    ).all()
    serializer_class = PerfilGenericoSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]

    filterset_fields = [
        'departamento',
        'subarea',
        'tipo',
        'estado'
    ]

    search_fields = [
        'nombre',
        'usuario',
        'correo',
        'departamento__nombre',
        'subarea__nombre',
        'dpto_area',
        'observaciones',
    ]

    def get_queryset(self):
        queryset = PerfilGenerico.objects.select_related(
            'departamento',
            'subarea',
        ).all()

        legacy_filter = self.request.query_params.get('dpto_area')
        if legacy_filter and legacy_filter.strip():
            value = legacy_filter.strip()

            if value.startswith('dept:'):
                try:
                    queryset = queryset.filter(
                        departamento_id=int(value.split(':', 1)[1])
                    )
                except (TypeError, ValueError):
                    return queryset.none()
            elif value.startswith('subarea:'):
                try:
                    queryset = queryset.filter(
                        subarea_id=int(value.split(':', 1)[1])
                    )
                except (TypeError, ValueError):
                    return queryset.none()
            else:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(departamento__nombre__icontains=value)
                    | Q(subarea__nombre__icontains=value)
                    | Q(dpto_area__icontains=value)
                )

        return queryset.order_by(
            'departamento__nombre',
            'subarea__nombre',
            'nombre',
            'usuario',
        )

    def perform_destroy(self, instance):
        # Perfil Genérico usa baja lógica: nunca se elimina físicamente desde
        # la API para conservar evidencia de que el perfil existió.
        instance.estado = 'INACTIVO'
        instance.save(update_fields=['estado'])


class PCGenericoViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    permission_classes = [PortalRolePermission]
    queryset = PCGenerico.objects.prefetch_related(
        'historial'
    ).all()

    serializer_class = PCGenericoSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]

    filterset_fields = [
        'dpto_area'
    ]

    search_fields = [
        'usuario_local',
        'hostname',
        'dpto_area',
        'marca',
        'modelo',
        'numero_serie',
        'activo_fijo',
        'teamviewer_id',
        'observaciones',
    ]

    def get_queryset(self):
        queryset = PCGenerico.objects.prefetch_related(
            'historial'
        ).all()

        dpto = self.request.query_params.get(
            'dpto_area',
            None
        )

        if dpto and dpto.strip():
            queryset = queryset.filter(
                dpto_area__icontains=dpto.strip()
            )

        return queryset