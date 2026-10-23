"""Notificaciones mínimas de cambios. REST sigue siendo la fuente de datos."""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from asgiref.sync import async_to_sync
from asgiref.sync import sync_to_async
from channels.consumer import get_handler_name
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from channels.security.websocket import OriginValidator
from django.db import transaction
from django.db import close_old_connections
from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError

from .authentication import PortalJWTAuthentication
from .client_ip import get_websocket_client_ip
from .permissions import ROLE_VIEWER, get_role
from .session_events import session_group_name


EDITOR_GROUP = 'portal_editors'
VIEWER_GROUP = 'portal_viewers'
logger = logging.getLogger(__name__)
AUTH_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix='portal-ws-auth')


class RealtimeDependencyError(RuntimeError):
    pass

MODULE_DEPENDENCIES = {
    'Usuario': ('usuarios', 'equipos', 'ips', 'anexos', 'activos-resumen'),
    'Equipamiento': ('equipos', 'usuarios', 'activos-resumen'),
    'IP': ('ips', 'usuarios', 'equipos', 'servidores', 'pcs-genericos'),
    'Servidor': ('servidores', 'ips'),
    'PCGenerico': ('pcs-genericos', 'ips'),
    'Anexo': ('anexos', 'usuarios'),
    'PerfilGenerico': ('perfiles',),
    'Departamento': ('departamentos', 'usuarios', 'perfiles', 'pcs-genericos', 'activos-resumen'),
    'SubArea': ('departamentos', 'usuarios', 'perfiles', 'pcs-genericos'),
    'RevisionBajaUsuario': ('revisiones-baja',),
}


def _acquire_connection_slot(key, limit):
    try:
        if limit <= 0:
            return False
        if cache.add(key, 1, timeout=3600):
            return True
        try:
            count = cache.incr(key)
        except ValueError:
            return cache.add(key, 1, timeout=3600)
        if count <= limit:
            return True
        cache.decr(key)
        return False
    except Exception as exc:
        raise RealtimeDependencyError('No se pudo comprobar el límite de conexiones.') from exc


def _release_connection_slot(key):
    if not key:
        return
    try:
        cache.decr(key)
    except ValueError:
        return
    except Exception as exc:
        raise RealtimeDependencyError('No se pudo liberar el límite de conexiones.') from exc


def _allow_message(key, limit):
    try:
        if limit <= 0:
            return False
        if cache.add(key, 1, timeout=1):
            return True
        try:
            return cache.incr(key) <= limit
        except ValueError:
            return cache.add(key, 1, timeout=1)
    except Exception as exc:
        raise RealtimeDependencyError('No se pudo comprobar el límite de mensajes.') from exc


def schedule_change(instance, operation):
    """Publica una vez confirmada la transacción, sin datos privados del registro."""
    modules = MODULE_DEPENDENCIES.get(type(instance).__name__)
    if not modules:
        return
    event_id = str(uuid.uuid4())
    record_id = instance.pk
    model = type(instance).__name__

    def publish():
        layer = get_channel_layer()
        if layer is None:
            return
        event = {
            'type': 'portal.change',
            'event_id': event_id,
            'model': model,
            'record_id': record_id,
            'operation': operation,
            'modules': modules,
        }
        try:
            async_to_sync(layer.group_send)(EDITOR_GROUP, event)
            if 'anexos' in modules:
                async_to_sync(layer.group_send)(VIEWER_GROUP, {
                    'type': 'portal.change',
                    'event_id': event_id,
                    'modules': ('anexos',),
                })
        except Exception:
            logger.exception('No se pudo enviar la notificación del cambio %s', event_id)

    transaction.on_commit(publish)


def _authenticate_portal_token_sync(raw_token):
    close_old_connections()
    try:
        authentication = PortalJWTAuthentication()
        validated = authentication.get_validated_token(raw_token)
        user = authentication.get_user(validated)
        role = get_role(user)
        return (
            role,
            int(validated['exp']),
            validated.get('user_id'),
            validated.get('sid'),
        ) if role else None
    except (AuthenticationFailed, TokenError, TypeError, KeyError):
        return None
    finally:
        close_old_connections()


async def authenticate_portal_token(raw_token):
    future = AUTH_EXECUTOR.submit(_authenticate_portal_token_sync, raw_token)
    # Python 3.14 del entorno DEV no despierta siempre al loop al terminar
    # consultas SQLite en run_in_executor; comprobamos solo durante esta tarea.
    deadline = asyncio.get_running_loop().time() + settings.PORTAL_WS_AUTH_TIMEOUT_SECONDS
    while not future.done() and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.02)
    if not future.done():
        future.cancel()
        raise TimeoutError('La autenticación WebSocket excedió el tiempo permitido.')
    return future.result()


class StrictPortalOriginValidator(OriginValidator):
    """Rechaza el handshake directamente, sin iniciar un consumidor extra."""

    async def __call__(self, scope, receive, send):
        origins = [value for name, value in scope.get('headers', []) if name.lower() == b'origin']
        try:
            valid = len(origins) == 1 and self.valid_origin(urlparse(origins[0].decode('latin1')))
        except (UnicodeDecodeError, ValueError):
            valid = False
        if not valid:
            await send({'type': 'websocket.close', 'code': 4403})
            return
        await self.application(scope, receive, send)


class PortalChangesConsumer(AsyncJsonWebsocketConsumer):
    async def dispatch(self, message):
        # La autenticación gestiona explícitamente sus conexiones de BD.
        handler = getattr(self, get_handler_name(message), None)
        if handler is None:
            logger.warning('websocket_unknown_event')
            await self.close(code=1011)
            return
        try:
            await handler(message)
        except StopConsumer:
            raise
        except Exception:
            logger.exception('websocket_unhandled_exception')
            await self.close(code=1011)

    async def connect(self):
        self.ip_slot_key = None
        self.user_slot_key = None
        self.client_ip = get_websocket_client_ip(self.scope) or 'unknown'
        candidate_key = f'ws:connections:ip:{self.client_ip}'
        try:
            acquired = await sync_to_async(_acquire_connection_slot)(
                candidate_key,
                settings.PORTAL_WS_MAX_CONNECTIONS_PER_IP,
            )
        except RealtimeDependencyError:
            logger.exception('websocket_security_cache_unavailable')
            await self.close(code=1013)
            return
        if not acquired:
            logger.warning('websocket_connection_rate_limited', extra={'client_ip': self.client_ip})
            await self.close(code=4429)
            return
        self.ip_slot_key = candidate_key
        self.authenticated = False
        self.auth_deadline = asyncio.create_task(self.close_if_unauthenticated())
        self.expiry_task = None
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if bytes_data is not None:
            await self.close(code=4400)
            return
        if text_data is None or len(text_data.encode('utf-8')) > settings.PORTAL_WS_MAX_MESSAGE_BYTES:
            await self.close(code=4400)
            return
        await super().receive(text_data=text_data, bytes_data=bytes_data, **kwargs)

    async def close_if_unauthenticated(self):
        await asyncio.sleep(5)
        if not self.authenticated:
            await self.close(code=4401)

    async def close_at_expiry(self, expires_at):
        await asyncio.sleep(max(0, expires_at - time.time()))
        await self.close(code=4401)

    async def receive_json(self, content, **kwargs):
        message_keys = [f'ws:messages:ip:{self.client_ip}']
        if getattr(self, 'user_id', None) is not None:
            message_keys.append(f'ws:messages:user:{self.user_id}')
        try:
            allowed = all([
                await sync_to_async(_allow_message)(
                    key,
                    settings.PORTAL_WS_MESSAGES_PER_SECOND,
                )
                for key in message_keys
            ])
        except RealtimeDependencyError:
            logger.exception('websocket_security_cache_unavailable')
            await self.close(code=1013)
            return
        if not allowed:
            logger.warning('websocket_message_rate_limited', extra={'client_ip': self.client_ip})
            await self.close(code=4429)
            return
        if not isinstance(content, dict):
            await self.close(code=4401)
            return
        if self.authenticated or set(content) != {'type', 'token'} or content.get('type') != 'auth':
            return
        raw_token = content.get('token', '')
        if not isinstance(raw_token, str) or len(raw_token) > 8192:
            await self.close(code=4401)
            return
        try:
            authenticated = await authenticate_portal_token(raw_token)
        except Exception:
            logger.exception('websocket_authentication_unavailable')
            await self.close(code=1013)
            return
        if authenticated is None:
            await self.close(code=4401)
            return
        role, expires_at, user_id, session_id = authenticated
        candidate_key = f'ws:connections:user:{user_id}'
        try:
            acquired = await sync_to_async(_acquire_connection_slot)(
                candidate_key,
                settings.PORTAL_WS_MAX_CONNECTIONS_PER_USER,
            )
        except RealtimeDependencyError:
            logger.exception('websocket_security_cache_unavailable')
            await self.close(code=1013)
            return
        if not acquired:
            logger.warning('websocket_user_connection_rate_limited', extra={'user_id': user_id})
            await self.close(code=4429)
            return
        group_name = VIEWER_GROUP if role == ROLE_VIEWER else EDITOR_GROUP
        session_group = session_group_name(session_id)
        added_groups = []
        try:
            await self.channel_layer.group_add(group_name, self.channel_name)
            added_groups.append(group_name)
            await self.channel_layer.group_add(session_group, self.channel_name)
            added_groups.append(session_group)
        except Exception:
            logger.exception('websocket_group_subscription_failed')
            for added_group in added_groups:
                try:
                    await self.channel_layer.group_discard(added_group, self.channel_name)
                except Exception:
                    logger.exception('websocket_group_cleanup_failed')
            try:
                await sync_to_async(_release_connection_slot)(candidate_key)
            except RealtimeDependencyError:
                logger.exception('websocket_slot_cleanup_failed')
            await self.close(code=1013)
            return
        self.user_slot_key = candidate_key
        self.user_id = user_id
        self.session_group = session_group
        self.group_name = group_name
        self.raw_token = raw_token
        self.role = role
        self.authenticated = True
        self.auth_deadline.cancel()
        self.expiry_task = asyncio.create_task(self.close_at_expiry(expires_at))
        await self.send_json({'type': 'ready'})

    async def portal_change(self, event):
        if not self.authenticated:
            return
        authenticated = await authenticate_portal_token(self.raw_token)
        if authenticated is None:
            await self.close(code=4401)
            return
        role, _, _, _ = authenticated
        if role != self.role:
            await self.close(code=4403)
            return
        await self.send_json({key: value for key, value in event.items() if key != 'type'} | {
            'type': 'change',
        })

    async def session_revoked(self, event):
        await self.close(code=4401)

    async def disconnect(self, close_code):
        if getattr(self, 'group_name', None):
            try:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            except Exception:
                logger.exception('websocket_group_cleanup_failed')
        if getattr(self, 'session_group', None):
            try:
                await self.channel_layer.group_discard(self.session_group, self.channel_name)
            except Exception:
                logger.exception('websocket_group_cleanup_failed')
        if getattr(self, 'auth_deadline', None):
            self.auth_deadline.cancel()
        if getattr(self, 'expiry_task', None):
            self.expiry_task.cancel()
        for slot_key in (
            getattr(self, 'user_slot_key', None),
            getattr(self, 'ip_slot_key', None),
        ):
            try:
                await sync_to_async(_release_connection_slot)(slot_key)
            except RealtimeDependencyError:
                logger.exception('websocket_slot_cleanup_failed')
