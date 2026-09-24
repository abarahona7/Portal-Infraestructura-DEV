"""Perfil explícito y validado para el despliegue productivo."""

import os

os.environ.setdefault('DJANGO_ENV', 'production')

from .settings import *  # noqa: F403, E402
