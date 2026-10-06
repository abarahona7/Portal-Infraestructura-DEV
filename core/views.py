from django.http import HttpResponse
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.db.models.functions import Length
from rest_framework.decorators import action

from .services.acta_entrega_pdf import (
    generar_acta_entrega_pdf
)

from rest_framework import viewsets, filters, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .permissions import PortalRolePermission
from .pagination import PortalPageNumberPagination
from .services.asignacion_ips import MANAGED_IP_SEGMENT_PREFIXES
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
    HistorialAsignacionIPSerializer,
    AnexoSerializer,
    PCGenericoSerializer,
    ServidorSerializer,
    DepartamentoSerializer,
    SubAreaSerializer,
    AnexoListSerializer,
    EquipamientoListSerializer,
    IPReferenceSerializer,
    PCGenericoListSerializer,
    ServidorListSerializer,
    PerfilGenericoReferenceSerializer,
    PerfilGenericoListSerializer,
    UsuarioListSerializer,
    UsuarioReferenceSerializer,
)

from .audit import (
    set_current_audit_user,
    reset_current_audit_user,
)
from .realtime import schedule_change
from .equipment_categories import EQUIPMENT_CATEGORY_TYPES

class AuditUserMixin:
    def perform_create(self, serializer):
        token = set_current_audit_user(
            self.request.user
        )

        try:
            with transaction.atomic():
                instance = serializer.save()
                schedule_change(instance, 'created')
        finally:
            reset_current_audit_user(token)

    def perform_update(self, serializer):
        token = set_current_audit_user(
            self.request.user
        )

        try:
            with transaction.atomic():
                instance = serializer.save()
                schedule_change(instance, 'updated')
        finally:
            reset_current_audit_user(token)

    def perform_destroy(self, instance):
        token = set_current_audit_user(
            self.request.user
        )

        try:
            with transaction.atomic():
                schedule_change(instance, 'deleted')
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
        if (
            instance.usuarios.exists()
            or instance.perfiles_genericos.exists()
            or instance.pcs_genericos.exists()
        ):
            raise serializers.ValidationError({
                'detail': (
                    'No se puede eliminar este departamento porque tiene '
                    'usuarios, perfiles genéricos o PCs asociados. Puedes desactivarlo.'
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
        if (
            instance.usuarios.exists()
            or instance.perfiles_genericos.exists()
            or instance.pcs_genericos.exists()
        ):
            raise serializers.ValidationError({
                'detail': (
                    'No se puede eliminar esta subárea porque tiene usuarios, '
                    'perfiles genéricos o PCs asociados. Puedes desactivarla para '
                    'conservar las relaciones existentes.'
                )
            })

        super().perform_destroy(instance)


class IPViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    permission_classes = [PortalRolePermission]
    queryset = IP.objects.select_related('usuario').all()
    serializer_class = IPSerializer
    pagination_class = PortalPageNumberPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]
    filterset_fields = ['estado']
    search_fields = [
        'direccion_ip',
        'observacion',
        'usuario__nombre_completo',
        'asignado_otro',
        'asignacion_activa__usuario__nombre_completo',
        'asignacion_activa__servidor__hostname',
        'asignacion_activa__pc_generico__hostname',
        'asignacion_activa__detalle',
    ]

    def get_queryset(self):
        queryset = IP.objects.select_related(
            'usuario',
            'asignacion_activa__usuario',
            'asignacion_activa__servidor',
            'asignacion_activa__pc_generico',
        )
        if self.action in {'retrieve', 'update', 'partial_update', 'destroy'}:
            queryset = queryset.select_related('servidor', 'pc_generico')
        segment_id = self.request.query_params.get('segmento', '').strip()
        prefix = MANAGED_IP_SEGMENT_PREFIXES.get(segment_id)
        if segment_id and not prefix:
            return queryset.none()
        if prefix:
            queryset = queryset.filter(direccion_ip__startswith=prefix)
            return queryset.annotate(
                _address_length=Length('direccion_ip')
            ).order_by('_address_length', 'direccion_ip')
        return queryset.order_by('direccion_ip')

    def perform_destroy(self, instance):
        with transaction.atomic():
            ip = IP.objects.select_for_update().get(pk=instance.pk)
            if (
                ip.estado != 'LIBRE'
                or ip.usuario_id
                or ip.asignado_otro
                or hasattr(ip, 'servidor')
                or hasattr(ip, 'pc_generico')
                or hasattr(ip, 'asignacion_activa')
            ):
                raise serializers.ValidationError({
                    'detail': (
                        'No se puede eliminar una IP reservada o asignada. '
                        'Libérala primero desde el módulo que administra su asignación.'
                    )
                })
            schedule_change(ip, 'deleted')
            ip.delete()

    @action(detail=True, methods=['get'], url_path='historial')
    def assignment_history(self, request, pk=None):
        ip = self.get_object()
        records = ip.historial_asignaciones.all()
        return Response(
            HistorialAsignacionIPSerializer(records, many=True).data
        )


# =========================================
# SERVIDORES
# =========================================

class ServidorViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    permission_classes = [PortalRolePermission]
    queryset = Servidor.objects.select_related('ip').all()
    serializer_class = ServidorSerializer
    pagination_class = PortalPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return ServidorListSerializer
        return ServidorSerializer

    def get_queryset(self):
        queryset = Servidor.objects.select_related('ip')
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('historial')
        return queryset

    filter_backends = [
        filters.SearchFilter
    ]

    search_fields = [
        'ip__direccion_ip',
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
    queryset = Anexo.objects.select_related('usuario').all()

    serializer_class = AnexoSerializer
    pagination_class = PortalPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return AnexoListSerializer
        return AnexoSerializer

    def get_queryset(self):
        queryset = Anexo.objects.select_related('usuario')
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('historial')
        return queryset

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
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    pagination_class = PortalPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return UsuarioListSerializer
        return UsuarioSerializer

    def get_queryset(self):
        equipment_queryset = Equipamiento.objects.select_related(
            'usuario',
            'usuario__ip',
        )

        if self.action == 'retrieve':
            equipment_queryset = equipment_queryset.prefetch_related('historial')

        queryset = Usuario.objects.select_related(
            'departamento',
            'subarea',
            'ip',
            'anexo_asignado',
        ).prefetch_related(
            Prefetch('equipos', queryset=equipment_queryset),
        )

        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('historial')

        department_filter = self.request.query_params.get('dpto_area')
        if department_filter and department_filter.strip():
            value = department_filter.strip()

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
                queryset = queryset.filter(
                    Q(departamento__nombre__iexact=value)
                    | Q(subarea__nombre__iexact=value)
                    | Q(dpto_area__iexact=value)
                )

        return queryset.order_by('nombre_completo', 'pk')

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]

    filterset_fields = [
        'departamento',
        'subarea',
        'estado'
    ]

    search_fields = [
        'nombre_completo',
        'usuario_red',
        'correo_corp',
        'celular',
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

        if not usuario.equipos.exists():
            return Response(
                {
                    'detail': (
                        'No se puede generar el Acta de Entrega porque el '
                        'usuario no tiene equipos o insumos asignados.'
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

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
    queryset = Equipamiento.objects.select_related('usuario', 'usuario__ip', 'usuario__departamento').all()
    serializer_class = EquipamientoSerializer
    pagination_class = PortalPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return EquipamientoListSerializer
        return EquipamientoSerializer

    def get_queryset(self):
        queryset = Equipamiento.objects.select_related('usuario', 'usuario__ip', 'usuario__departamento')
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('historial')
        category = self.request.query_params.get('categoria', '').strip()
        if category:
            allowed_types = EQUIPMENT_CATEGORY_TYPES.get(category)
            if not allowed_types:
                return queryset.none()
            queryset = queryset.filter(tipo__in=allowed_types)
        department_id = self.request.query_params.get('departamento_id')
        if department_id is not None:
            if not department_id.isdecimal() or int(department_id) < 1:
                raise serializers.ValidationError({'departamento_id': 'Indique un departamento válido.'})
            queryset = queryset.filter(usuario__departamento_id=int(department_id))
        pending = self.request.query_params.get('pendiente')
        if pending == 'sin_serie':
            queryset = queryset.filter(Q(numero_serie__isnull=True) | Q(numero_serie=''))
        elif pending == 'sin_activo_fijo':
            queryset = queryset.filter(Q(af__isnull=True) | Q(af=''))
        elif pending == 'sin_custodio':
            queryset = queryset.filter(usuario__isnull=True)
        elif pending == 'custodio_no_activo':
            queryset = queryset.filter(usuario__isnull=False).exclude(usuario__estado='ACTIVO')
        elif pending:
            raise serializers.ValidationError({'pendiente': 'Seleccione un motivo de revisión válido.'})
        return queryset.order_by('tipo', 'marca', 'modelo', 'pk')

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
    pagination_class = PortalPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return PerfilGenericoListSerializer
        return PerfilGenericoSerializer

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

        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('historial')

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

class PCGenericoViewSet(
    AuditUserMixin,
    viewsets.ModelViewSet
):
    permission_classes = [PortalRolePermission]
    queryset = PCGenerico.objects.select_related(
        'ip',
        'departamento',
        'subarea',
    ).prefetch_related(
        'historial'
    ).all()

    serializer_class = PCGenericoSerializer
    pagination_class = PortalPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return PCGenericoListSerializer
        return PCGenericoSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter
    ]

    filterset_fields = [
        'departamento',
        'subarea',
        'dpto_area',
    ]

    search_fields = [
        'usuario_local',
        'hostname',
        'dpto_area',
        'departamento__nombre',
        'subarea__nombre',
        'marca',
        'modelo',
        'numero_serie',
        'activo_fijo',
        'teamviewer_id',
        'observaciones',
        'ip__direccion_ip',
    ]

    def get_queryset(self):
        queryset = PCGenerico.objects.select_related(
            'ip',
            'departamento',
            'subarea',
        )

        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('historial')

        dpto = self.request.query_params.get('dpto_area')

        if dpto and dpto.strip():
            value = dpto.strip()
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
                queryset = queryset.filter(
                    Q(departamento__nombre__icontains=value)
                    | Q(subarea__nombre__icontains=value)
                    | Q(dpto_area__icontains=value)
                )

        return queryset.order_by(
            'departamento__nombre',
            'subarea__nombre',
            'usuario_local',
            'pk',
        )


class ReferenceDataView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request):
        requested = request.query_params.get('include', '')
        sections = {
            item.strip()
            for item in requested.split(',')
            if item.strip()
        } or {'usuarios', 'ips', 'departamentos', 'perfiles'}

        payload = {}

        if 'usuarios' in sections:
            users = Usuario.objects.select_related(
                'departamento',
                'subarea',
            ).all()
            payload['usuarios'] = UsuarioReferenceSerializer(
                users,
                many=True,
            ).data

        if 'usuarios_stats' in sections:
            department_counts = {}
            total_users = 0
            rows = Usuario.objects.values(
                'departamento__nombre',
                'dpto_area',
            ).annotate(total=Count('id'))

            for row in rows:
                department_name = (
                    row['departamento__nombre']
                    or row['dpto_area']
                    or 'Sin Departamento'
                ).strip() or 'Sin Departamento'
                row_total = row['total']
                department_counts[department_name] = (
                    department_counts.get(department_name, 0) + row_total
                )
                total_users += row_total

            payload['usuarios_stats'] = {
                'total': total_users,
                'departamentos': [
                    {
                        'nombre': name,
                        'total': count,
                    }
                    for name, count in department_counts.items()
                ],
            }

        if 'ips' in sections:
            ips = IP.objects.only(
                'id',
                'direccion_ip',
                'estado',
                'observacion',
            ).all()
            payload['ips'] = IPReferenceSerializer(ips, many=True).data

        if 'departamentos' in sections:
            departments = Departamento.objects.prefetch_related(
                Prefetch(
                    'subareas',
                    queryset=SubArea.objects.select_related('departamento'),
                )
            ).all()
            payload['departamentos'] = DepartamentoSerializer(
                departments,
                many=True,
            ).data

        if 'perfiles' in sections:
            profiles = PerfilGenerico.objects.select_related(
                'departamento',
                'subarea',
            ).all()
            payload['perfiles'] = PerfilGenericoReferenceSerializer(
                profiles,
                many=True,
            ).data

        if 'ips_stats' in sections:
            stats = {
                segment_id: {'total': 0, 'libres': 0, 'reservadas': 0}
                for segment_id in MANAGED_IP_SEGMENT_PREFIXES
            }
            for address, state in IP.objects.values_list(
                'direccion_ip',
                'estado',
            ).iterator():
                segment_id = next((
                    key
                    for key, prefix in MANAGED_IP_SEGMENT_PREFIXES.items()
                    if address.startswith(prefix)
                ), None)
                if not segment_id:
                    continue
                stats[segment_id]['total'] += 1
                if state == 'LIBRE':
                    stats[segment_id]['libres'] += 1
                elif state == 'RESERVADA':
                    stats[segment_id]['reservadas'] += 1
            payload['ips_stats'] = stats

        return Response(payload)
