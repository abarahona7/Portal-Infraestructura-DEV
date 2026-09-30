"""API de movimientos y documentos persistidos del inventario TI."""
import csv
import uuid
from datetime import datetime, time
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, OperationalError
from django.db.models import Prefetch, Q
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from .models import ActaEntrega, ActaEstadoEvento, ESTADOS_FISICOS, MovimientoActivo, TIPOS_MOVIMIENTO, Usuario
from .pagination import PortalPageNumberPagination
from .permissions import PortalRolePermission
from .services.acta_estado_service import (
    actas_pendientes_firma, estado_vigente, registrar_estado_acta, resumen_acta_pendiente,
)


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
    estado = serializers.SerializerMethodField()
    fecha_cierre = serializers.SerializerMethodField()
    tiene_copia_firmada = serializers.SerializerMethodField()

    class Meta:
        model = ActaEntrega
        fields = ['id', 'folio', 'tipo_movimiento', 'estado', 'fecha_emision',
                  'fecha_cierre', 'colaborador_id', 'usuario_ti_id', 'hash_verificacion',
                  'tiene_copia_firmada']
        read_only_fields = fields

    def get_estado(self, obj):
        return estado_vigente(obj)

    def get_fecha_cierre(self, obj):
        eventos = getattr(obj, '_eventos_estado', None)
        if eventos is None:
            eventos = obj.estado_eventos.all()
        return next((evento.fecha for evento in eventos if evento.estado_nuevo == 'CERRADA'), obj.fecha_cierre)

    def get_tiene_copia_firmada(self, obj):
        eventos = getattr(obj, '_eventos_estado', None)
        if eventos is None:
            eventos = obj.estado_eventos.all()
        return any(evento.hash_copia_firmada for evento in eventos)


class ActaEstadoEventoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()

    def get_usuario_nombre(self, obj):
        return obj.usuario.get_full_name() or obj.usuario.get_username()

    class Meta:
        model = ActaEstadoEvento
        fields = ['id', 'estado_anterior', 'estado_nuevo', 'fecha', 'usuario_id', 'usuario_nombre',
                  'motivo', 'hash_copia_firmada']
        read_only_fields = fields


class CambioEstadoActaSerializer(serializers.Serializer):
    estado_nuevo = serializers.ChoiceField(choices=['PENDIENTE_FIRMA', 'FIRMADA', 'CERRADA', 'ANULADA'])
    motivo = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    archivo_firmado = serializers.FileField(required=False)


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


class ReporteMovimientosSerializer(serializers.Serializer):
    desde = serializers.DateField(required=False)
    hasta = serializers.DateField(required=False)
    tipo_movimiento = serializers.ChoiceField(choices=TIPOS_MOVIMIENTO, required=False)

    def validate(self, attrs):
        if attrs.get('desde') and attrs.get('hasta') and attrs['desde'] > attrs['hasta']:
            raise serializers.ValidationError({'hasta': 'La fecha final debe ser igual o posterior a la inicial.'})
        return attrs


class _CsvBuffer:
    def write(self, value):
        return value


def _csv_cell(value):
    """Evita fórmulas al abrir campos editables por usuarios en una planilla."""
    value = '' if value is None else str(value)
    if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')):
        return "'" + value
    return value


def _reporte_movimientos_rows(queryset):
    writer = csv.writer(_CsvBuffer(), delimiter=';')
    yield '\ufeff'
    yield writer.writerow(['ID movimiento', 'Fecha y hora', 'Tipo', 'ID activo', 'Equipo actual', 'Serie actual',
                           'Activo fijo actual', 'Custodio origen', 'Custodio destino', 'Ubicación origen',
                           'Ubicación destino', 'Estado resultante', 'Folio', 'Ejecutado por'])
    fields = ('id', 'fecha_movimiento', 'tipo_movimiento', 'activo_id', 'activo__tipo',
              'activo__marca', 'activo__modelo', 'activo__numero_serie', 'activo__af',
              'colaborador_origen__nombre_completo', 'colaborador_destino__nombre_completo',
              'ubicacion_origen', 'ubicacion_destino', 'estado_operativo_resultante',
              'acta__folio', 'ejecutado_por')
    for row in queryset.values_list(*fields).iterator(chunk_size=1000):
        (movement_id, date, kind, asset_id, asset_type, brand, model, serial, af,
         origin, destination, origin_place, destination_place, state, folio, actor) = row
        values = (movement_id, timezone.localtime(date).strftime('%Y-%m-%d %H:%M:%S'), kind,
                  asset_id, ' '.join(part for part in (asset_type, brand, model) if part), serial,
                  af, origin, destination, origin_place, destination_place, state, folio, actor)
        yield writer.writerow([_csv_cell(value) for value in values])


class MovimientoActivoViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                              mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [PortalRolePermission]
    pagination_class = PortalPageNumberPagination
    serializer_class = MovimientoSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = MovimientoActivo.objects.select_related('acta').defer('acta__documento_pdf').prefetch_related(
            Prefetch('acta__estado_eventos', queryset=ActaEstadoEvento.objects.defer('copia_firmada_pdf'),
                     to_attr='_eventos_estado'))
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

    @action(detail=False, methods=['get'])
    def custodias(self, request):
        from .services.colaborador_custodia_service import periodos_custodia
        colaborador_id = _filter_id(request, 'colaborador_id')
        if colaborador_id is None:
            raise serializers.ValidationError({'colaborador_id': 'Indique el colaborador.'})
        get_object_or_404(Usuario.objects.only('id'), pk=colaborador_id)
        return Response(periodos_custodia(colaborador_id))

    @action(detail=False, methods=['get'])
    def reporte(self, request):
        filters = ReporteMovimientosSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = MovimientoActivo.objects.all().order_by('-fecha_movimiento', '-pk')
        params = filters.validated_data
        if params.get('desde'):
            start = timezone.make_aware(datetime.combine(params['desde'], time.min))
            queryset = queryset.filter(fecha_movimiento__gte=start)
        if params.get('hasta'):
            end = timezone.make_aware(datetime.combine(params['hasta'], time.max))
            queryset = queryset.filter(fecha_movimiento__lte=end)
        if params.get('tipo_movimiento'):
            queryset = queryset.filter(tipo_movimiento=params['tipo_movimiento'])
        response = StreamingHttpResponse(_reporte_movimientos_rows(queryset), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="movimientos-itam-{timezone.localdate():%Y%m%d}.csv"'
        response['Cache-Control'] = 'no-store, private'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

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
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = ActaEntrega.objects.defer('documento_pdf').prefetch_related(
            Prefetch('estado_eventos', queryset=ActaEstadoEvento.objects.select_related('usuario').defer('copia_firmada_pdf'),
                     to_attr='_eventos_estado'))
        colaborador_id = _filter_id(self.request, 'colaborador_id')
        if colaborador_id:
            queryset = queryset.filter(colaborador_id=colaborador_id)
        return queryset

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        page = self.paginate_queryset(actas_pendientes_firma())
        response = self.get_paginated_response([resumen_acta_pendiente(acta) for acta in page])
        response['Cache-Control'] = 'no-store, private'
        return response

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


    @action(detail=True, methods=['get'])
    def eventos(self, request, pk=None):
        acta = self.get_object()
        return Response(ActaEstadoEventoSerializer(acta._eventos_estado, many=True).data)

    @action(detail=True, methods=['post'], parser_classes=[JSONParser, FormParser, MultiPartParser])
    def estado(self, request, pk=None):
        acta = self.get_object()
        serializer = CambioEstadoActaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registrar_estado_acta(acta_id=acta.pk, usuario=request.user, request=request, **serializer.validated_data)
        acta = self.get_queryset().get(pk=acta.pk)
        return Response(ActaSerializer(acta).data)

    @action(detail=True, methods=['get'])
    def firmada(self, request, pk=None):
        acta = self.get_object()
        evento = acta.estado_eventos.filter(estado_nuevo='FIRMADA').first()
        if not evento or not evento.copia_firmada_pdf:
            return Response({'detail': 'Esta acta no tiene una copia firmada cargada.'}, status=404)
        response = HttpResponse(bytes(evento.copia_firmada_pdf), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{acta.folio}-copia-firmada.pdf"'
        response['Cache-Control'] = 'no-store, private'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
