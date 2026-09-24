import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .permissions import get_role
from .models import PortalSession, SecurityAuditLog
from .session_auth import (
    PortalSessionError,
    get_active_portal_session,
    revoke_portal_session,
    touch_portal_session,
)


logger = logging.getLogger(__name__)


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


def _expired_session_response():
    response = Response(
        {'detail': 'Sesión expirada.'},
        status=status.HTTP_401_UNAUTHORIZED,
    )
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE,
        path=settings.JWT_COOKIE_PATH,
    )
    return response


class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        response = Response({'csrfToken': get_token(request)})
        response['Cache-Control'] = 'no-store, private'
        return response


@method_decorator(csrf_protect, name='dispatch')
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
        portal_session = PortalSession.objects.create(user=user)
        refresh = RefreshToken.for_user(user)
        refresh['sid'] = str(portal_session.pk)
        response = Response({'access': str(refresh.access_token), 'user': {'username': user.get_username(), 'role': role}})
        _set_refresh_cookie(response, refresh)
        return response


@method_decorator(csrf_protect, name='dispatch')
class RefreshCookieView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if not raw:
            return _expired_session_response()
        try:
            old = RefreshToken(raw)
            user_id = old.get('user_id')
            portal_session = get_active_portal_session(
                old.get('sid'),
                user_id=user_id,
            )
            user = get_user_model().objects.get(pk=user_id)
            if not user.is_active or not get_role(user):
                raise TokenError('Usuario sin acceso')
            if request.headers.get('X-Portal-Activity') == '1':
                touch_portal_session(portal_session)
            try:
                old.blacklist()
            except AttributeError:
                pass
            new = RefreshToken.for_user(user)
            new['sid'] = str(portal_session.pk)
            response = Response({'access': str(new.access_token), 'user': {'username': user.get_username(), 'role': get_role(user)}})
            _set_refresh_cookie(response, new)
            return response
        except (
            TokenError,
            PortalSessionError,
            get_user_model().DoesNotExist,
            ValueError,
            TypeError,
        ) as exc:
            logger.warning(
                'session_refresh_rejected',
                extra={
                    'event': 'SESSION_REFRESH_REJECTED',
                    'reason': type(exc).__name__,
                },
            )
            return _expired_session_response()
        except Exception:
            logger.exception(
                'session_refresh_unexpected_error',
                extra={'event': 'SESSION_REFRESH_ERROR'},
            )
            return Response(
                {'detail': 'No fue posible renovar la sesión.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


@method_decorator(csrf_protect, name='dispatch')
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if raw:
            try:
                refresh = RefreshToken(raw)
                revoke_portal_session(refresh.get('sid'))
                refresh.blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.JWT_REFRESH_COOKIE, path=settings.JWT_COOKIE_PATH)
        return response


class ActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        portal_session = get_active_portal_session(
            request.auth.get('sid'),
            user_id=request.user.pk,
        )
        touch_portal_session(portal_session)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'username': request.user.get_username(), 'role': get_role(request.user)})
