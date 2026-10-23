"""Perfil explícito y validado para el despliegue productivo."""

import os

# Este módulo representa una decisión explícita de despliegue. No debe heredar
# un DJANGO_ENV residual del shell, systemd o un contenedor.
os.environ['DJANGO_ENV'] = 'production'

from .settings import *  # noqa: F403, E402
