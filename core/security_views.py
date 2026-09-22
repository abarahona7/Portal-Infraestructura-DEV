from django.contrib.auth import authenticate
from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .crypto import decrypt_val
from .models import Usuario, Equipamiento, PerfilGenerico, PCGenerico, SecurityAuditLog
from .permissions import is_admin

SECRET_MAP = {
    'usuario': {'password_gmail': (Usuario, 'password_gmail'), 'password_vpn': (Usuario, 'password_vpn')},
    'perfil-generico': {'password': (PerfilGenerico, 'password')},
    'pc-generico': {'password': (PCGenerico, 'password')},
    'equipamiento': {'icloud_password': (Equipamiento, 'icloud_password'), 'pin': (Equipamiento, 'pin')},
}


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')


def _audit(request, success, module, object_id, secret_type, detail=''):
    SecurityAuditLog.objects.create(
        event='SECRET_REVEAL', actor=request.user.get_username(), module=module,
        object_id_text=str(object_id), secret_type=secret_type, success=success,
        detail=detail[:255], ip_address=_client_ip(request),
    )


class RevealSecretView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'secret_reveal'

    def post(self, request):
        module = request.data.get('module')
        object_id = request.data.get('object_id')
        secret_type = request.data.get('secret_type')
        password = request.data.get('password', '')

        if not is_admin(request.user):
            _audit(request, False, module, object_id, secret_type, 'ROL_NO_AUTORIZADO')
            return Response({'detail': 'No autorizado.'}, status=status.HTTP_403_FORBIDDEN)

        # La identidad siempre se toma de request.user; nunca del payload.
        verified = authenticate(request=request, username=request.user.get_username(), password=password)
        if verified is None or verified.pk != request.user.pk:
            _audit(request, False, module, object_id, secret_type, 'REAUTENTICACION_FALLIDA')
            return Response({'detail': 'Contraseña de sesión incorrecta.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            model, field = SECRET_MAP[module][secret_type]
            obj = model.objects.get(pk=object_id)
        except (KeyError, ValueError, TypeError):
            _audit(request, False, module, object_id, secret_type, 'SECRETO_NO_VALIDO')
            raise Http404
        except model.DoesNotExist:
            _audit(request, False, module, object_id, secret_type, 'REGISTRO_NO_EXISTE')
            raise Http404

        encrypted = getattr(obj, field, None)
        secret = decrypt_val(encrypted) if encrypted else ''
        _audit(request, True, module, object_id, secret_type, 'OK')
        response = Response({'secret': secret, 'expires_in': 30})
        response['Cache-Control'] = 'no-store, private'
        response['Pragma'] = 'no-cache'
        return response
