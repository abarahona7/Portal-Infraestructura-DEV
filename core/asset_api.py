"""API de movimientos y documentos persistidos del inventario TI."""
import uuid
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, OperationalError
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from .models import ActaEntrega, ESTADOS_FISICOS, MovimientoActivo
from .pagination import PortalPageNumberPagination
from .permissions import PortalRolePermission


class MovimientoConflictResponse(APIException):
    status_code = status.HTTP_409_CONFLICT


class AccesorioSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=100)
    entregado = serializers.BooleanField()
    nota = serializers.CharField(max_length=300, required=False, allow_blank=True)


class NuevoMovimientoSerializer(serializers.Serializer):
    tipo_movimiento = serializers.ChoiceField(choices=['ASIGNACION', 'PRESTAMO', 'DEVOLUCION', 'REASIGNACION',
                                                      'INGRESO_REPARACION', 'SALIDA_REPARACION', 'BAJA'])
    activo_id = serializers.IntegerField(min_value=1)
    colaborador_destino_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    colaborador_origen_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    ubicacion_destino = serializers.CharField(max_length=100)
    estado_fisico = serializers.ChoiceField(choices=ESTADOS_FISICOS)
    estado_operativo_resultante = serializers.ChoiceField(
        choices=['STOCK', 'MANTENCION', 'ASIGNADO', 'PRESTAMO', 'BAJA'], required=False)
    accesorios_detalle = AccesorioSerializer(many=True, max_length=50)
    observaciones = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    def validate(self, attrs):
        kind = attrs['tipo_movimiento']
        if kind in {'ASIGNACION', 'PRESTAMO', 'REASIGNACION'} and not attrs.get('colaborador_destino_id'):
            raise serializers.ValidationError({'colaborador_destino_id': 'Seleccione el colaborador que recibe.'})
        if kind in {'DEVOLUCION', 'REASIGNACION'} and not attrs.get('colaborador_origen_id'):
            raise serializers.ValidationError({'colaborador_origen_id': 'Indique al custodio actual.'})
        if kind in {'INGRESO_REPARACION', 'SALIDA_REPARACION', 'BAJA'} and not attrs.get('observaciones', '').strip():
            raise serializers.ValidationError({'observaciones': 'Indique el motivo o trabajo realizado.'})
        if attrs['estado_fisico'] == 'DANADO' and not attrs.get('observaciones', '').strip():
            raise serializers.ValidationError({'observaciones': 'Describa los daños del activo.'})
        return attrs


class CambioEquipoSerializer(serializers.Serializer):
    activo_origen_id = serializers.IntegerField(min_value=1)
    activo_destino_id = serializers.IntegerField(min_value=1)
    colaborador_id = serializers.IntegerField(min_value=1)
    ubicacion_retorno = serializers.CharField(max_length=100)
    ubicacion_entrega = serializers.CharField(max_length=100)
    estado_fisico_origen = serializers.ChoiceField(choices=ESTADOS_FISICOS)
    estado_fisico_destino = serializers.ChoiceField(choices=ESTADOS_FISICOS)
    estado_operativo_origen = serializers.ChoiceField(choices=['STOCK', 'MANTENCION'], required=False)
    accesorios_devueltos = AccesorioSerializer(many=True, max_length=50)
    accesorios_entregados = AccesorioSerializer(many=True, max_length=50)
    observaciones = serializers.CharField(max_length=2000)

    def validate(self, attrs):
        if attrs['activo_origen_id'] == attrs['activo_destino_id']:
            raise serializers.ValidationError({'activo_destino_id': 'Seleccione otro equipo de reemplazo.'})
        if not attrs['observaciones'].strip():
            raise serializers.ValidationError({'observaciones': 'Indique el motivo del cambio.'})
        return attrs


class ActaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActaEntrega
        fields = ['id', 'folio', 'tipo_movimiento', 'estado', 'fecha_emision',
                  'fecha_cierre', 'colaborador_id', 'usuario_ti_id', 'hash_verificacion']
        read_only_fields = fields


class MovimientoSerializer(serializers.ModelSerializer):
    acta = ActaSerializer(read_only=True)
    colaborador_origen = serializers.SerializerMethodField()
    colaborador_destino = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoActivo
        fields = ['id', 'activo_id', 'tipo_movimiento', 'fecha_movimiento',
                  'operacion_id', 'colaborador_origen_id', 'colaborador_destino_id',
                  'colaborador_origen', 'colaborador_destino', 'ubicacion_origen',
                  'ubicacion_destino', 'estado_fisico', 'estado_operativo_resultante',
                  'accesorios_detalle', 'observaciones', 'ejecutado_por', 'acta', 'snapshot']
        read_only_fields = fields

    def get_colaborador_origen(self, obj):
        return obj.snapshot.get('colaborador_origen')

    def get_colaborador_destino(self, obj):
        return obj.snapshot.get('colaborador_destino')


def _filter_id(request, name):
    value = request.query_params.get(name)
    if value is None:
        return None
    try:
        value = int(value)
        if value < 1:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise serializers.ValidationError({name: 'Debe ser un identificador entero positivo.'})


class MovimientoActivoViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                              mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [PortalRolePermission]
    pagination_class = PortalPageNumberPagination
    serializer_class = MovimientoSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = MovimientoActivo.objects.select_related('acta').defer('acta__documento_pdf')
        activo_id = _filter_id(self.request, 'activo_id')
        colaborador_id = _filter_id(self.request, 'colaborador_id')
        if activo_id:
            queryset = queryset.filter(activo_id=activo_id)
        if colaborador_id:
            queryset = queryset.filter(Q(colaborador_origen_id=colaborador_id) |
                                       Q(colaborador_destino_id=colaborador_id))
        operation = self.request.query_params.get('operacion_id')
        if operation:
            try:
                operation = uuid.UUID(operation)
            except (ValueError, TypeError, AttributeError) as exc:
                raise serializers.ValidationError({'operacion_id': 'Indique un UUID válido.'}) from exc
            queryset = queryset.filter(operacion_id=operation)
        return queryset

    def create(self, request, *args, **kwargs):
        from .services.asset_lifecycle_service import MovimientoConflict, registrar_movimiento
        serializer = NuevoMovimientoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            movimiento = registrar_movimiento(usuario_ti=request.user, request=request,
                                              **serializer.validated_data)
        except MovimientoConflict as exc:
            raise MovimientoConflictResponse({'codigo': exc.codigo, 'detail': exc.detail}) from exc
        except DjangoValidationError as exc:
            raise serializers.ValidationError(getattr(exc, 'message_dict', None) or exc.messages) from exc
        except IntegrityError as exc:
            raise MovimientoConflictResponse({'codigo': 'CONFLICTO_INTEGRIDAD',
                'detail': 'Los datos cambiaron o existe un identificador duplicado. Actualice y vuelva a intentar.'}) from exc
        except OperationalError as exc:
            if exc.args and exc.args[0] in (1205, 1213):
                raise MovimientoConflictResponse({'codigo': 'CONFLICTO_CONCURRENCIA',
                    'detail': 'Otra operación está modificando estos datos. Actualice y vuelva a intentar.'}) from exc
            raise
        return Response(MovimientoSerializer(movimiento).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='cambio')
    def cambio(self, request):
        from .services.asset_change_service import registrar_cambio_equipo
        from .services.asset_lifecycle_service import MovimientoConflict
        serializer = CambioEquipoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            operation_id, returned, issued = registrar_cambio_equipo(
                usuario_ti=request.user, request=request, **serializer.validated_data)
        except MovimientoConflict as exc:
            raise MovimientoConflictResponse({'codigo': exc.codigo, 'detail': exc.detail}) from exc
        except DjangoValidationError as exc:
            raise serializers.ValidationError(getattr(exc, 'message_dict', None) or exc.messages) from exc
        except IntegrityError as exc:
            raise MovimientoConflictResponse({'codigo': 'CONFLICTO_INTEGRIDAD',
                'detail': 'Los datos cambiaron durante la operación. Actualice y vuelva a intentar.'}) from exc
        except OperationalError as exc:
            if exc.args and exc.args[0] in (1205, 1213):
                raise MovimientoConflictResponse({'codigo': 'CONFLICTO_CONCURRENCIA',
                    'detail': 'Otra operación está modificando estos datos. Actualice y vuelva a intentar.'}) from exc
            raise
        return Response({
            'tipo_operacion': 'CAMBIO', 'operacion_id': str(operation_id),
            'salida': MovimientoSerializer(returned).data,
            'entrada': MovimientoSerializer(issued).data,
        }, status=status.HTTP_201_CREATED)


class ActaEntregaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [PortalRolePermission]
    pagination_class = PortalPageNumberPagination
    serializer_class = ActaSerializer
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        queryset = ActaEntrega.objects.defer('documento_pdf')
        colaborador_id = _filter_id(self.request, 'colaborador_id')
        if colaborador_id:
            queryset = queryset.filter(colaborador_id=colaborador_id)
        return queryset

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        acta = self.get_object()
        if not acta.documento_pdf:
            return Response({'detail': 'Esta acta no tiene un documento persistido.'}, status=409)
        response = HttpResponse(bytes(acta.documento_pdf), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{acta.folio}.pdf"'
        response['Cache-Control'] = 'no-store, private'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
