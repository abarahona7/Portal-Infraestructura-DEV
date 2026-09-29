"""Consulta autenticada y etiqueta QR para la ficha de un activo."""
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse
from reportlab.graphics import renderSVG
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Equipamiento
from .permissions import PortalRolePermission


class AssetQrSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='usuario.nombre_completo')
    usuario_departamento = serializers.ReadOnlyField(source='usuario.dpto_area')

    class Meta:
        model = Equipamiento
        fields = ('id', 'tipo', 'marca', 'modelo', 'numero_serie', 'af', 'estado',
                  'estado_fisico', 'ubicacion_actual', 'accesorios',
                  'usuario_nombre', 'usuario_departamento')


def _asset_url(token):
    base = settings.PORTAL_PUBLIC_URL
    parts = urlsplit(base)
    if (not parts.netloc or parts.scheme not in {'http', 'https'} or parts.username
            or parts.password or parts.query or parts.fragment or parts.path not in ('', '/')
            or (settings.IS_PRODUCTION and parts.scheme != 'https')):
        return None
    return f'{base}/qr/a/{token}'


class AssetQrView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request, token):
        try:
            asset = Equipamiento.objects.select_related('usuario').get(token_qr=token)
        except Equipamiento.DoesNotExist:
            return Response({'detail': 'Activo no encontrado.'}, status=404)
        url = _asset_url(token)
        if url is None:
            return Response({'detail': 'Configure PORTAL_PUBLIC_URL para generar etiquetas QR.'}, status=503)
        response = Response({'activo': AssetQrSerializer(asset).data, 'qr_url': url})
        response['Cache-Control'] = 'no-store, private'
        return response


class AssetQrImageView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request, token):
        if not Equipamiento.objects.filter(token_qr=token).exists():
            return Response({'detail': 'Activo no encontrado.'}, status=404)
        url = _asset_url(token)
        if url is None:
            return Response({'detail': 'Configure PORTAL_PUBLIC_URL para generar etiquetas QR.'}, status=503)
        qr = QrCodeWidget(url)
        left, bottom, right, top = qr.getBounds()
        size = 160
        drawing = Drawing(size, size, transform=[size / (right - left), 0, 0,
                                                 size / (top - bottom), 0, 0])
        drawing.add(qr)
        response = HttpResponse(renderSVG.drawToString(drawing), content_type='image/svg+xml; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="activo-{token}.svg"'
        response['Cache-Control'] = 'no-store, private'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'"
        return response
