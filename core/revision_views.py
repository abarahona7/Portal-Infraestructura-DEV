"""Revisión compartida de recursos liberados por estados de usuario."""

import math

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import HistorialUsuario, RevisionBajaUsuario
from .permissions import PortalRolePermission
from .realtime import schedule_change


class RevisionBajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevisionBajaUsuario
        fields = (
            'id', 'motivo', 'usuario_nombre', 'usuario_red', 'recursos', 'creado_por',
            'creado_en', 'revisado_por', 'revisado_en',
        )


class RevisionesBajaView(APIView):
    permission_classes = [PortalRolePermission]

    def get(self, request):
        page = request.query_params.get('page', '1')
        if not page.isdecimal() or int(page) < 1:
            return Response({'detail': 'Página inválida.'}, status=400)
        page = min(int(page), 100000)
        estado = request.query_params.get('estado', 'pendientes')
        if estado not in {'pendientes', 'revisadas'}:
            return Response({'detail': 'Estado inválido.'}, status=400)
        pendientes = RevisionBajaUsuario.objects.filter(revisado_en__isnull=True).count()
        queryset = RevisionBajaUsuario.objects.filter(revisado_en__isnull=(estado == 'pendientes'))
        count = queryset.count()
        page_size = 25
        total_pages = max(math.ceil(count / page_size), 1)
        items = [] if page > total_pages else queryset[(page - 1) * page_size:page * page_size]
        response = Response({
            'pendientes': pendientes,
            'count': count,
            'page': page,
            'page_size': page_size,
            'results': RevisionBajaSerializer(items, many=True).data,
        })
        response['Cache-Control'] = 'no-store, private'
        return response


class ConfirmarRevisionBajaView(APIView):
    permission_classes = [PortalRolePermission]

    def post(self, request, pk):
        confirmaciones = request.data.get('confirmaciones')
        if not isinstance(confirmaciones, list) or not all(isinstance(item, str) for item in confirmaciones):
            return Response({'confirmaciones': 'Debes confirmar cada recurso de la lista.'}, status=400)
        with transaction.atomic():
            try:
                revision = RevisionBajaUsuario.objects.select_for_update().get(pk=pk)
            except RevisionBajaUsuario.DoesNotExist:
                return Response({'detail': 'Revisión no encontrada.'}, status=404)
            if revision.revisado_en:
                return Response({'detail': 'Esta liberación ya fue revisada por otra persona.'}, status=409)
            claves = {recurso['clave'] for recurso in revision.recursos}
            if len(confirmaciones) != len(claves) or set(confirmaciones) != claves:
                return Response({'confirmaciones': 'Confirma todos los recursos antes de finalizar.'}, status=400)
            revision.revisado_en = timezone.now()
            revision.revisado_por = request.user.get_username()
            revision.save(update_fields=['revisado_en', 'revisado_por'])
            HistorialUsuario.objects.create(
                usuario=revision.usuario, accion=f'REVISION_{revision.motivo}_CONFIRMADA',
                modificado_por=revision.revisado_por,
                modulo_relacionado='revisiones-baja',
                objeto_relacionado_id=str(revision.pk),
                observacion=f'Revisión confirmada de {len(claves)} recurso(s) liberado(s).',
            )
            schedule_change(revision, 'updated')
        response = Response(RevisionBajaSerializer(revision).data, status=status.HTTP_200_OK)
        response['Cache-Control'] = 'no-store, private'
        return response
