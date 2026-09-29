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
        )

        def distribution(queryset, field):
            grouped = list(queryset.values(field).annotate(total=Count('pk')).order_by('-total', field)[:10])
            entries = [{'nombre': row[field] or 'Sin registrar', 'total': row['total']} for row in grouped]
            remaining = queryset.count() - sum(entry['total'] for entry in entries)
            if remaining:
                entries.append({'nombre': 'Otros', 'total': remaining})
            return entries

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
