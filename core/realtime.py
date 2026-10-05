"""Notificaciones mínimas de cambios. REST sigue siendo la fuente de datos."""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from asgiref.sync import async_to_sync
from channels.consumer import get_handler_name
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from channels.security.websocket import OriginValidator
from django.db import transaction
from django.db import close_old_connections
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError

from .authentication import PortalJWTAuthentication
from .permissions import ROLE_VIEWER, get_role


EDITOR_GROUP = 'portal_editors'
VIEWER_GROUP = 'portal_viewers'
logger = logging.getLogger(__name__)
AUTH_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix='portal-ws-auth')

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
}


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
                    **event,
                    'modules': ('anexos',),
                    'record_id': record_id if model == 'Anexo' else None,
                    'model': 'Anexo' if model == 'Anexo' else 'Relacionado',
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
        return (role, int(validated['exp'])) if role else None
    except (AuthenticationFailed, TokenError, TypeError, KeyError):
        return None
    finally:
        close_old_connections()


async def authenticate_portal_token(raw_token):
    future = AUTH_EXECUTOR.submit(_authenticate_portal_token_sync, raw_token)
    # Python 3.14 del entorno DEV no despierta siempre al loop al terminar
    # consultas SQLite en run_in_executor; comprobamos solo durante esta tarea.
    while not future.done():
        await asyncio.sleep(0.02)
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
            raise ValueError(f'Evento WebSocket desconocido: {message["type"]}')
        await handler(message)

    async def connect(self):
        self.authenticated = False
        self.auth_deadline = asyncio.create_task(self.close_if_unauthenticated())
        self.expiry_task = None
        await self.accept()

    async def close_if_unauthenticated(self):
        await asyncio.sleep(5)
        if not self.authenticated:
            await self.close(code=4401)

    async def close_at_expiry(self, expires_at):
        await asyncio.sleep(max(0, expires_at - time.time()))
        await self.close(code=4401)

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            await self.close(code=4401)
            return
        if self.authenticated or content.get('type') != 'auth':
            return
        raw_token = content.get('token', '')
        if not isinstance(raw_token, str) or len(raw_token) > 8192:
            await self.close(code=4401)
            return
        authenticated = await authenticate_portal_token(raw_token)
        if authenticated is None:
            await self.close(code=4401)
            return
        role, expires_at = authenticated
        self.authenticated = True
        self.raw_token = raw_token
        self.role = role
        self.auth_deadline.cancel()
        self.group_name = VIEWER_GROUP if role == ROLE_VIEWER else EDITOR_GROUP
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        self.expiry_task = asyncio.create_task(self.close_at_expiry(expires_at))
        await self.send_json({'type': 'ready'})

    async def portal_change(self, event):
        if not self.authenticated:
            return
        authenticated = await authenticate_portal_token(self.raw_token)
        if authenticated is None:
            await self.close(code=4401)
            return
        role, _ = authenticated
        if role != self.role:
            await self.close(code=4403)
            return
        await self.send_json({key: value for key, value in event.items() if key != 'type'} | {
            'type': 'change',
        })

    async def disconnect(self, close_code):
        if getattr(self, 'group_name', None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if getattr(self, 'auth_deadline', None):
            self.auth_deadline.cancel()
        if getattr(self, 'expiry_task', None):
            self.expiry_task.cancel()
