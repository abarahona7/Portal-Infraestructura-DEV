import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .permissions import HasPortalRole, get_role
from .models import PortalSession
from .session_auth import (
    PortalSessionError,
    get_active_portal_session,
    revoke_portal_session,
    touch_portal_session,
)
from .throttles import LoginIPThrottle, LoginUsernameThrottle, RefreshIPThrottle
from .session_events import notify_session_revoked
from .security_events import record_security_event
from .token_storage import redact_outstanding_token


logger = logging.getLogger(__name__)


def _user_payload(user, role=None):
    return {
        'username': user.get_username(),
        'display_name': user.get_full_name().strip() or user.get_username(),
        'role': role or get_role(user),
    }


def _cookie_kwargs():
    return dict(
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path=settings.JWT_COOKIE_PATH,
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
    )


def _set_refresh_cookie(response, token):
    response.set_cookie(settings.JWT_REFRESH_COOKIE, str(token), **_cookie_kwargs())


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
    throttle_classes = [LoginIPThrottle, LoginUsernameThrottle]
    throttle_scope = 'login'

    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        user = authenticate(request=request, username=username, password=password)
        if not user:
            record_security_event(
                request=request, event='LOGIN_FAILED', actor=username,
                module='auth', success=False, detail='CREDENCIALES_INVALIDAS',
            )
            return Response({'detail': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)
        role = get_role(user)
        if not role:
            record_security_event(
                request=request, event='LOGIN_FAILED', actor=user.get_username(),
                module='auth', success=False, detail='ROL_NO_AUTORIZADO',
            )
            return Response({'detail': 'Usuario autenticado sin rol del portal.'}, status=status.HTTP_403_FORBIDDEN)
        portal_session = PortalSession.objects.create(user=user)
        refresh = RefreshToken.for_user(user)
        refresh['sid'] = str(portal_session.pk)
        redact_outstanding_token(refresh)
        response = Response({'access': str(refresh.access_token), 'user': _user_payload(user, role)})
        _set_refresh_cookie(response, refresh)
        record_security_event(
            request=request, event='LOGIN_SUCCESS', actor=user.get_username(),
            role=role, module='auth', object_id=portal_session.pk,
            success=True, detail='OK',
        )
        return response


@method_decorator(csrf_protect, name='dispatch')
class RefreshCookieView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RefreshIPThrottle]
    throttle_scope = 'refresh'

    def post(self, request):
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if not raw:
            return _expired_session_response()
        try:
            candidate = RefreshToken(raw)
            user_id = candidate.get('user_id')
            # Persiste una eventual expiración por inactividad antes del bloqueo.
            get_active_portal_session(candidate.get('sid'), user_id=user_id)
            with transaction.atomic():
                portal_session = get_active_portal_session(
                    candidate.get('sid'),
                    user_id=user_id,
                    for_update=True,
                )
                # Revalida bajo bloqueo para rechazar reutilización concurrente.
                old = RefreshToken(raw)
                user = get_user_model().objects.get(pk=user_id)
                if not user.is_active or not get_role(user):
                    raise TokenError('Usuario sin acceso')
                if request.headers.get('X-Portal-Activity') == '1':
                    touch_portal_session(portal_session)
                old.blacklist()
                new = RefreshToken.for_user(user)
                new['sid'] = str(portal_session.pk)
                redact_outstanding_token(new)
            response = Response({'access': str(new.access_token), 'user': _user_payload(user)})
            _set_refresh_cookie(response, new)
            record_security_event(
                request=request, event='SESSION_REFRESH', actor=user.get_username(),
                role=get_role(user), module='auth', object_id=portal_session.pk,
                success=True, detail='ROTATED',
            )
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
            record_security_event(
                request=request, event='SESSION_REFRESH', module='auth',
                success=False, detail=type(exc).__name__,
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
        success = True
        detail = 'NO_COOKIE'
        actor = ''
        session_id = None
        if raw:
            try:
                refresh = RefreshToken(raw)
                session_id = refresh.get('sid')
                actor = f'user_id:{refresh.get("user_id", "unknown")}'
                revoke_portal_session(session_id)
                notify_session_revoked(session_id)
                refresh.blacklist()
                detail = 'REVOKED'
            except TokenError:
                detail = 'INVALID_TOKEN'
            except Exception as exc:
                success = False
                detail = type(exc).__name__
                logger.exception(
                    'session_logout_unexpected_error',
                    extra={'event': 'SESSION_LOGOUT_ERROR'},
                )
        record_security_event(
            request=request, event='LOGOUT', actor=actor, module='auth',
            object_id=session_id or '', success=success, detail=detail,
        )
        response = Response(
            {'detail': 'No fue posible confirmar el cierre de sesión.'} if not success else None,
            status=(
                status.HTTP_503_SERVICE_UNAVAILABLE
                if not success else status.HTTP_204_NO_CONTENT
            ),
        )
        response.delete_cookie(settings.JWT_REFRESH_COOKIE, path=settings.JWT_COOKIE_PATH)
        return response


class ActivityView(APIView):
    permission_classes = [IsAuthenticated, HasPortalRole]

    def post(self, request):
        portal_session = get_active_portal_session(
            request.auth.get('sid'),
            user_id=request.user.pk,
        )
        touch_portal_session(portal_session)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated, HasPortalRole]

    def get(self, request):
        return Response(_user_payload(request.user))
