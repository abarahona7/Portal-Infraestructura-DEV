"""Resumen agregado del inventario TI, calculado sobre el maestro vigente."""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Equipamiento, MovimientoActivo
from .permissions import PortalRolePermission


class AssetDashboardView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request):
        assets = Equipamiento.objects.all()
        activos_vigentes = ~Q(estado='BAJA')
        sin_imei_celular = Q(tipo='Celular') & (Q(imei__isnull=True) | Q(imei=''))
        sin_hostname_computador = Q(tipo__in=['Notebook', 'Mac']) & (Q(hostname__isnull=True) | Q(hostname=''))
        sin_mac_computador = Q(tipo__in=['Notebook', 'Mac']) & (Q(mac_address__isnull=True) | Q(mac_address=''))
        ficha_incompleta = activos_vigentes & (sin_imei_celular | sin_hostname_computador | sin_mac_computador)
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
            con_custodio_inactivo=Count('pk', filter=Q(usuario__isnull=False) & ~Q(usuario__estado='ACTIVO')),
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

        pendientes = []
        for asset in assets.filter(ficha_incompleta).only(
            'id', 'tipo', 'marca', 'modelo', 'numero_serie', 'af', 'estado',
            'imei', 'hostname', 'mac_address',
        ).order_by('-pk')[:10]:
            faltantes = []
            if asset.tipo == 'Celular' and not asset.imei:
                faltantes.append('IMEI')
            if asset.tipo in {'Notebook', 'Mac'}:
                if not asset.hostname:
                    faltantes.append('Hostname')
                if not asset.mac_address:
                    faltantes.append('MAC Address')
            pendientes.append({
                'id': asset.pk, 'tipo': asset.tipo, 'marca': asset.marca,
                'modelo': asset.modelo, 'numero_serie': asset.numero_serie,
                'af': asset.af, 'estado': asset.estado, 'faltantes': faltantes,
            })

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
