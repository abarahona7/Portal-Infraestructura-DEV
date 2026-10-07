"""Ficha QR y resumen breve del inventario de equipos existente."""
from urllib.parse import urlsplit

from django.conf import settings
from django.db.models import Count, Q
from django.http import HttpResponse
from reportlab.graphics import renderSVG
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Departamento, Equipamiento
from .permissions import PortalRolePermission


class FichaEquipoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    departamento = serializers.SerializerMethodField()

    class Meta:
        model = Equipamiento
        fields = ('id', 'tipo', 'marca', 'modelo', 'numero_serie', 'af', 'estado',
                  'hostname', 'imei', 'numero_telefono', 'accesorios',
                  'usuario_nombre', 'departamento')

    def get_usuario_nombre(self, obj):
        return obj.usuario.nombre_completo if obj.usuario_id else None

    def get_departamento(self, obj):
        return obj.usuario.departamento.nombre if obj.usuario_id else None


def _public_url(token):
    base = settings.PORTAL_PUBLIC_URL
    parts = urlsplit(base)
    if (parts.scheme not in {'http', 'https'} or not parts.netloc or parts.username
            or parts.password or parts.query or parts.fragment or parts.path not in ('', '/')
            or (settings.IS_PRODUCTION and parts.scheme != 'https')):
        return None
    return f'{base}/qr/a/{token}'


class FichaEquipoQrView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request, token):
        try:
            equipo = Equipamiento.objects.select_related('usuario__departamento').get(token_qr=token)
        except Equipamiento.DoesNotExist:
            return Response({'detail': 'Equipo no encontrado.'}, status=404)
        url = _public_url(token)
        if url is None:
            return Response({'detail': 'Configure PORTAL_PUBLIC_URL para usar las etiquetas QR.'}, status=503)
        response = Response({'equipo': FichaEquipoSerializer(equipo).data, 'qr_url': url})
        response['Cache-Control'] = 'no-store, private'
        return response


class EtiquetaEquipoQrView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request, token):
        if not Equipamiento.objects.filter(token_qr=token).exists():
            return Response({'detail': 'Equipo no encontrado.'}, status=404)
        url = _public_url(token)
        if url is None:
            return Response({'detail': 'Configure PORTAL_PUBLIC_URL para usar las etiquetas QR.'}, status=503)
        qr = QrCodeWidget(url)
        left, bottom, right, top = qr.getBounds()
        size = 160
        drawing = Drawing(size, size, transform=[size / (right - left), 0, 0,
                                                 size / (top - bottom), 0, 0])
        drawing.add(qr)
        response = HttpResponse(renderSVG.drawToString(drawing), content_type='image/svg+xml; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="equipo-{token}.svg"'
        response['Cache-Control'] = 'no-store, private'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'"
        return response


class ResumenEquiposView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request):
        equipos = Equipamiento.objects.all()
        counts = equipos.aggregate(
            total=Count('id'),
            asignados=Count('id', filter=Q(usuario__isnull=False)),
            disponibles=Count('id', filter=Q(estado='STOCK')),
            reparacion=Count('id', filter=Q(estado='MANTENCION')),
            baja=Count('id', filter=Q(estado='BAJA')),
            sin_serie=Count('id', filter=Q(numero_serie__isnull=True) | Q(numero_serie='')),
            sin_activo_fijo=Count('id', filter=Q(af__isnull=True) | Q(af='')),
            sin_custodio=Count('id', filter=Q(usuario__isnull=True)),
            custodio_no_activo=Count('id', filter=Q(usuario__isnull=False) & ~Q(usuario__estado='ACTIVO')),
        )
        departamentos = Departamento.objects.annotate(
            total=Count('usuarios__equipos', distinct=True),
        ).order_by('-total', 'nombre')
        response = Response({
            'conteos': counts,
            'departamentos': [{'id': row.id, 'nombre': row.nombre, 'total': row.total}
                              for row in departamentos],
        })
        response['Cache-Control'] = 'no-store, private'
        return response
