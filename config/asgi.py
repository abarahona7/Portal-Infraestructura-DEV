"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings
from django.urls import path
from core.realtime import PortalChangesConsumer, StrictPortalOriginValidator

allowed_origins = list(settings.CORS_ALLOWED_ORIGINS)
if settings.PORTAL_PUBLIC_URL:
    allowed_origins.append(settings.PORTAL_PUBLIC_URL)

application = ProtocolTypeRouter({
    'http': django_application,
    'websocket': StrictPortalOriginValidator(
        URLRouter([path('ws/changes/', PortalChangesConsumer.as_asgi())]),
        allowed_origins,
    ),
})
