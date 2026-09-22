from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .permissions import get_role
from .models import SecurityAuditLog


def _cookie_kwargs():
    return dict(
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path=settings.JWT_COOKIE_PATH,
    )


def _set_refresh_cookie(response, token):
    response.set_cookie(settings.JWT_REFRESH_COOKIE, str(token), **_cookie_kwargs())


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        user = authenticate(request=request, username=username, password=password)
        if not user:
            SecurityAuditLog.objects.create(event='LOGIN_FAILED', actor=username[:150], success=False, ip_address=_client_ip(request))
            return Response({'detail': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)
        role = get_role(user)
        if not role:
            return Response({'detail': 'Usuario autenticado sin rol del portal.'}, status=status.HTTP_403_FORBIDDEN)
        refresh = RefreshToken.for_user(user)
        response = Response({'access': str(refresh.access_token), 'user': {'username': user.get_username(), 'role': role}})
        _set_refresh_cookie(response, refresh)
        return response


class RefreshCookieView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if not raw:
            return Response({'detail': 'Sesión expirada.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            old = RefreshToken(raw)
            user_id = old.get('user_id')
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.get(pk=user_id)
            if not user.is_active or not get_role(user):
                raise TokenError('Usuario sin acceso')
            try:
                old.blacklist()
            except AttributeError:
                pass
            new = RefreshToken.for_user(user)
            response = Response({'access': str(new.access_token), 'user': {'username': user.get_username(), 'role': get_role(user)}})
            _set_refresh_cookie(response, new)
            return response
        except Exception:
            response = Response({'detail': 'Sesión expirada.'}, status=status.HTTP_401_UNAUTHORIZED)
            response.delete_cookie(settings.JWT_REFRESH_COOKIE, path=settings.JWT_COOKIE_PATH)
            return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.JWT_REFRESH_COOKIE, path=settings.JWT_COOKIE_PATH)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'username': request.user.get_username(), 'role': get_role(request.user)})
