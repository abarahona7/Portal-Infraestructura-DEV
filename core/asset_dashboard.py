"""Resumen agregado del inventario TI, calculado sobre el maestro vigente."""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Equipamiento, MovimientoActivo
from .pagination import PortalPageNumberPagination
from .permissions import PortalRolePermission
from .services.acta_estado_service import actas_pendientes_firma, resumen_acta_pendiente


CUSTODIO_NO_ACTIVO = Q(usuario__isnull=False) & ~Q(usuario__estado='ACTIVO')
GARANTIA_VENTANA_DIAS = 30


def _warranty_assets(queryset, condition, *, missing=False):
    assets = queryset.filter(condition).only(
        'id', 'tipo', 'marca', 'modelo', 'numero_serie', 'af',
        'estado', 'fecha_vencimiento_garantia',
    )
    return assets.order_by('-pk') if missing else assets.order_by('fecha_vencimiento_garantia', 'pk')


def _serialize_warranty(asset, today):
    return {
        'id': asset.pk, 'tipo': asset.tipo, 'marca': asset.marca,
        'modelo': asset.modelo, 'numero_serie': asset.numero_serie,
        'af': asset.af, 'estado': asset.estado,
        'fecha_vencimiento_garantia': asset.fecha_vencimiento_garantia,
        'dias_para_vencer': ((asset.fecha_vencimiento_garantia - today).days
                            if asset.fecha_vencimiento_garantia else None),
    }


def _warranty_conditions(today):
    vigente = ~Q(estado='BAJA')
    con_fecha = Q(fecha_vencimiento_garantia__isnull=False)
    proximas = vigente & con_fecha & Q(fecha_vencimiento_garantia__gte=today) & Q(
        fecha_vencimiento_garantia__lte=today + timedelta(days=GARANTIA_VENTANA_DIAS))
    vencidas = vigente & con_fecha & Q(fecha_vencimiento_garantia__lt=today)
    sin_fecha = vigente & Q(fecha_vencimiento_garantia__isnull=True)
    return proximas, vencidas, sin_fecha


class AssetWarrantyView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request):
        state = request.query_params.get('estado', 'proximas')
        if state not in {'proximas', 'vencidas', 'sin_fecha'}:
            raise ValidationError({'estado': 'Indique proximas, vencidas o sin_fecha.'})
        today = timezone.localdate()
        upcoming, expired, missing = _warranty_conditions(today)
        condition = {'proximas': upcoming, 'vencidas': expired, 'sin_fecha': missing}[state]
        paginator = PortalPageNumberPagination()
        page = paginator.paginate_queryset(
            _warranty_assets(Equipamiento.objects.all(), condition, missing=state == 'sin_fecha'),
            request, view=self,
        )
        response = paginator.get_paginated_response([_serialize_warranty(asset, today) for asset in page])
        response['Cache-Control'] = 'no-store, private'
        return response


def _inactive_custody_assets(queryset):
    return queryset.filter(CUSTODIO_NO_ACTIVO).select_related('usuario').only(
        'id', 'tipo', 'marca', 'modelo', 'numero_serie', 'af', 'estado',
        'ubicacion_actual', 'usuario', 'usuario__nombre_completo', 'usuario__estado',
    ).order_by('-pk')


def _serialize_inactive_custody(asset):
    return {
        'id': asset.pk, 'tipo': asset.tipo, 'marca': asset.marca,
        'modelo': asset.modelo, 'numero_serie': asset.numero_serie,
        'af': asset.af, 'estado': asset.estado,
        'ubicacion_actual': asset.ubicacion_actual,
        'colaborador': {
            'id': asset.usuario_id,
            'nombre_completo': asset.usuario.nombre_completo,
            'estado': asset.usuario.estado or 'SIN_ESTADO',
        },
    }


class AssetInactiveCustodianView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request):
        paginator = PortalPageNumberPagination()
        queryset = _inactive_custody_assets(Equipamiento.objects.all())
        page = paginator.paginate_queryset(queryset, request, view=self)
        response = paginator.get_paginated_response([_serialize_inactive_custody(asset) for asset in page])
        response['Cache-Control'] = 'no-store, private'
        return response


def _technical_missing_rules():
    vigente = ~Q(estado='BAJA')
    sin_imei = Q(tipo='Celular') & (Q(imei__isnull=True) | Q(imei=''))
    sin_hostname = Q(tipo__in=['Notebook', 'Mac']) & (Q(hostname__isnull=True) | Q(hostname=''))
    sin_mac = Q(tipo__in=['Notebook', 'Mac']) & (Q(mac_address__isnull=True) | Q(mac_address=''))
    return vigente, sin_imei, sin_hostname, sin_mac, vigente & (sin_imei | sin_hostname | sin_mac)


def _pending_assets(queryset):
    return queryset.only(
        'id', 'tipo', 'marca', 'modelo', 'numero_serie', 'af', 'estado',
        'imei', 'hostname', 'mac_address',
    ).order_by('-pk')


def _serialize_pending(asset):
    faltantes = []
    if asset.tipo == 'Celular' and not asset.imei:
        faltantes.append('IMEI')
    if asset.tipo in {'Notebook', 'Mac'}:
        if not asset.hostname:
            faltantes.append('Hostname')
        if not asset.mac_address:
            faltantes.append('MAC Address')
    return {
        'id': asset.pk, 'tipo': asset.tipo, 'marca': asset.marca,
        'modelo': asset.modelo, 'numero_serie': asset.numero_serie,
        'af': asset.af, 'estado': asset.estado, 'faltantes': faltantes,
    }


class AssetTechnicalPendingView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request):
        ficha_incompleta = _technical_missing_rules()[-1]
        paginator = PortalPageNumberPagination()
        queryset = _pending_assets(Equipamiento.objects.filter(ficha_incompleta))
        page = paginator.paginate_queryset(queryset, request, view=self)
        response = paginator.get_paginated_response([_serialize_pending(asset) for asset in page])
        response['Cache-Control'] = 'no-store, private'
        return response


class AssetDashboardView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request):
        assets = Equipamiento.objects.all()
        (activos_vigentes, sin_imei_celular, sin_hostname_computador,
         sin_mac_computador, ficha_incompleta) = _technical_missing_rules()
        today = timezone.localdate()
        garantias_proximas, garantias_vencidas, garantias_sin_fecha = _warranty_conditions(today)
        counts = assets.aggregate(
            total=Count('pk'),
            disponibles=Count('pk', filter=Q(estado='STOCK')),
            asignados=Count('pk', filter=Q(estado='ASIGNADO')),
            en_reparacion=Count('pk', filter=Q(estado='MANTENCION')),
            en_prestamo=Count('pk', filter=Q(estado='PRESTAMO')),
            dados_de_baja=Count('pk', filter=Q(estado='BAJA')),
            sin_serie=Count('pk', filter=Q(numero_serie__isnull=True) | Q(numero_serie='')),
            sin_activo_fijo=Count('pk', filter=Q(af__isnull=True) | Q(af='')),
            sin_custodio=Count('pk', filter=Q(usuario__isnull=True)),
            con_custodio_inactivo=Count('pk', filter=CUSTODIO_NO_ACTIVO),
            garantias_proximas=Count('pk', filter=garantias_proximas),
            garantias_vencidas=Count('pk', filter=garantias_vencidas),
            garantias_sin_fecha=Count('pk', filter=garantias_sin_fecha),
            sin_imei_celular=Count('pk', filter=activos_vigentes & sin_imei_celular),
            sin_hostname_computador=Count('pk', filter=activos_vigentes & sin_hostname_computador),
            sin_mac_computador=Count('pk', filter=activos_vigentes & sin_mac_computador),
            fichas_tecnicas_incompletas=Count('pk', filter=ficha_incompleta),
        )

        def distribution(queryset, field):
            grouped = list(queryset.values(field).annotate(total=Count('pk')).order_by('-total', field)[:10])
            entries = [{'nombre': row[field] or 'Sin registrar', 'total': row['total']} for row in grouped]
            remaining = queryset.count() - sum(entry['total'] for entry in entries)
            if remaining:
                entries.append({'nombre': 'Otros', 'total': remaining})
            return entries

        pendientes = [_serialize_pending(asset) for asset in _pending_assets(assets.filter(ficha_incompleta))[:10]]
        actas_pendientes = actas_pendientes_firma()
        custodios_no_activos = _inactive_custody_assets(assets)

        recent = MovimientoActivo.objects.select_related('activo', 'acta').defer('acta__documento_pdf')[:8]
        movements = [{
            'id': movement.pk,
            'activo_id': movement.activo_id,
            'activo': ' '.join(filter(None, [movement.activo.tipo, movement.activo.marca, movement.activo.modelo])),
            'tipo_movimiento': movement.tipo_movimiento,
            'fecha_movimiento': movement.fecha_movimiento,
            'folio': movement.acta.folio if movement.acta_id else None,
            'acta_id': movement.acta_id,
        } for movement in recent]
        response = Response({
            'conteos': counts,
            'pendientes_tecnicos': pendientes,
            'ventana_garantia_dias': GARANTIA_VENTANA_DIAS,
            'garantias_proximas_recientes': [
                _serialize_warranty(asset, today) for asset in _warranty_assets(assets, garantias_proximas)[:8]
            ],
            'garantias_vencidas_recientes': [
                _serialize_warranty(asset, today) for asset in _warranty_assets(assets, garantias_vencidas)[:8]
            ],
            'garantias_sin_fecha_recientes': [
                _serialize_warranty(asset, today) for asset in _warranty_assets(
                    assets, garantias_sin_fecha, missing=True)[:8]
            ],
            'custodios_no_activos_recientes': [
                _serialize_inactive_custody(asset) for asset in custodios_no_activos[:8]
            ],
            'actas_pendientes_firma': actas_pendientes.count(),
            'actas_pendientes_recientes': [resumen_acta_pendiente(acta) for acta in actas_pendientes[:8]],
            'por_tipo': distribution(assets, 'tipo'),
            'por_ubicacion': distribution(assets, 'ubicacion_actual'),
            'por_area': distribution(assets.filter(usuario__isnull=False), 'usuario__dpto_area'),
            'movimientos_30_dias': MovimientoActivo.objects.filter(
                fecha_movimiento__gte=timezone.now() - timedelta(days=30)).count(),
            'ultimos_movimientos': movements,
            'actualizado_en': timezone.now(),
        })
        response['Cache-Control'] = 'no-store, private'
        return response
