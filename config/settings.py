import os
import re
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path):
    """Carga variables locales sin reemplazar las definidas por el sistema."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].strip()
        if '=' not in line:
            continue

        name, value = line.split('=', 1)
        name = name.strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        elif ' #' in value:
            value = value.split(' #', 1)[0].rstrip()

        os.environ.setdefault(name, value)


load_env_file(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


def require_env(name):
    value = os.getenv(name, '').strip()
    if not value:
        raise ImproperlyConfigured(f'{name} es obligatorio en producción.')
    return value


DJANGO_ENV = os.getenv('DJANGO_ENV', 'development').strip().lower()
if DJANGO_ENV not in {'development', 'test', 'production'}:
    raise ImproperlyConfigured(
        'DJANGO_ENV debe ser development, test o production.'
    )

IS_PRODUCTION = DJANGO_ENV == 'production'
DEBUG = env_bool('DJANGO_DEBUG', not IS_PRODUCTION)
if IS_PRODUCTION and DEBUG:
    raise ImproperlyConfigured('DJANGO_DEBUG debe ser False en producción.')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or (secrets.token_urlsafe(50) if DEBUG else '')
if not SECRET_KEY:
    raise RuntimeError('DJANGO_SECRET_KEY es obligatorio cuando DJANGO_DEBUG=False.')
if IS_PRODUCTION and (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith('django-insecure-')
    or SECRET_KEY.startswith('replace-with-')
):
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY debe ser aleatoria, tener al menos 50 caracteres y no ser un placeholder.'
    )

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost' if DEBUG else '')
if IS_PRODUCTION and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS es obligatorio en producción.')

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.RequestContextMiddleware',
    'core.middleware.AdminLoginRateLimitMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.AuditActorMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_REDIS_URL = os.getenv('PORTAL_CHANNEL_REDIS_URL', '').strip()
if IS_PRODUCTION and not CHANNEL_REDIS_URL:
    raise ImproperlyConfigured('PORTAL_CHANNEL_REDIS_URL es obligatorio para WebSockets en producción.')
CHANNEL_LAYERS = {'default': (
    {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [CHANNEL_REDIS_URL], 'prefix': 'siminfra'},
    }
    if CHANNEL_REDIS_URL else
    {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
)}

PORTAL_CACHE_URL = os.getenv('PORTAL_CACHE_URL', '').strip()
if IS_PRODUCTION and not PORTAL_CACHE_URL:
    raise ImproperlyConfigured('PORTAL_CACHE_URL es obligatorio para límites compartidos en producción.')
CACHES = {
    'default': (
        {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': PORTAL_CACHE_URL,
            'KEY_PREFIX': 'siminfra',
        }
        if PORTAL_CACHE_URL else
        {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'siminfra-development',
        }
    )
}

DB_ENGINE = os.getenv('DATABASE_ENGINE', 'mysql' if IS_PRODUCTION else 'sqlite').lower()
if IS_PRODUCTION and DB_ENGINE not in {'mysql', 'django.db.backends.mysql'}:
    raise ImproperlyConfigured('Producción requiere DATABASE_ENGINE=mysql.')

if DB_ENGINE in {'mysql', 'django.db.backends.mysql'}:
    database_name = os.getenv('DATABASE_NAME', 'siminfra_db').strip()
    database_user = os.getenv('DATABASE_USER', 'siminfra_user').strip()
    database_password = os.getenv('DATABASE_PASSWORD', '')
    database_host = os.getenv('DATABASE_HOST', 'db').strip()
    if IS_PRODUCTION:
        for variable, value in {
            'DATABASE_NAME': database_name,
            'DATABASE_USER': database_user,
            'DATABASE_PASSWORD': database_password,
            'DATABASE_HOST': database_host,
        }.items():
            if not value:
                raise ImproperlyConfigured(f'{variable} es obligatorio en producción.')

    mysql_options = {
        'charset': 'utf8mb4',
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        'isolation_level': 'read committed',
    }
    database_ssl_ca = os.getenv('DATABASE_SSL_CA', '').strip()
    if database_ssl_ca:
        mysql_options['ssl'] = {'ca': database_ssl_ca}

    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': database_name,
        'USER': database_user,
        'PASSWORD': database_password,
        'HOST': database_host,
        'PORT': os.getenv('DATABASE_PORT', '3306'),
        'CONN_MAX_AGE': int(os.getenv('DATABASE_CONN_MAX_AGE', '60')),
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': mysql_options,
    }}
else:
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('SQLITE_PATH', str(BASE_DIR / 'db.sqlite3')),
    }}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'core.password_validation.NoCurrentPasswordReuseValidator'},
]

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = os.getenv('DJANGO_TIME_ZONE', 'America/Santiago')
USE_I18N = True
USE_TZ = True
PORTAL_PUBLIC_URL = os.getenv('PORTAL_PUBLIC_URL', 'http://localhost:5178' if not IS_PRODUCTION else '').rstrip('/')
if IS_PRODUCTION:
    try:
        public_url = urlsplit(PORTAL_PUBLIC_URL)
        public_port_is_valid = public_url.port is None or 1 <= public_url.port <= 65535
    except ValueError as exc:
        raise ImproperlyConfigured(
            'PORTAL_PUBLIC_URL debe ser la URL HTTPS pública del frontend, sin ruta ni parámetros.'
        ) from exc
    if (
        public_url.scheme != 'https'
        or not public_url.hostname
        or not public_port_is_valid
        or public_url.username is not None
        or public_url.password is not None
        or public_url.path
        or public_url.query
        or public_url.fragment
        or any(character.isspace() for character in PORTAL_PUBLIC_URL)
    ):
        raise ImproperlyConfigured(
            'PORTAL_PUBLIC_URL debe ser la URL HTTPS pública del frontend, sin ruta ni parámetros.'
        )
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5178,http://127.0.0.1:5178' if DEBUG else ''
)
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['X-Request-ID']
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.authentication.PortalJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'core.throttles.PortalUserRateThrottle',
        'core.throttles.PortalAnonRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'login_ip': os.getenv('LOGIN_IP_THROTTLE_RATE', '1000/min' if DJANGO_ENV == 'test' else '10/min'),
        'login_username': os.getenv('LOGIN_USERNAME_THROTTLE_RATE', '1000/min' if DJANGO_ENV == 'test' else '5/15min'),
        'admin_login_ip': os.getenv('ADMIN_LOGIN_IP_THROTTLE_RATE', '1000/min' if DJANGO_ENV == 'test' else '10/min'),
        'admin_login_username': os.getenv('ADMIN_LOGIN_USERNAME_THROTTLE_RATE', '1000/min' if DJANGO_ENV == 'test' else '5/15min'),
        'refresh': os.getenv('REFRESH_THROTTLE_RATE', '10/min'),
        'secret_reveal': os.getenv('SECRET_REVEAL_THROTTLE_RATE', '5/min'),
        'heavy': os.getenv('HEAVY_OPERATION_THROTTLE_RATE', '20/hour'),
        'api_user': os.getenv('API_USER_THROTTLE_RATE', '1200/hour'),
        'api_anon': os.getenv('API_ANON_THROTTLE_RATE', '60/hour'),
    },
    'EXCEPTION_HANDLER': 'core.exceptions.portal_exception_handler',
}

JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY', '').strip()
if IS_PRODUCTION:
    if (
        len(JWT_SIGNING_KEY) < 50
        or len(set(JWT_SIGNING_KEY)) < 5
        or JWT_SIGNING_KEY in {SECRET_KEY, os.getenv('FIELD_ENCRYPTION_KEY', '')}
        or JWT_SIGNING_KEY.startswith('replace-with-')
    ):
        raise ImproperlyConfigured(
            'JWT_SIGNING_KEY debe ser aleatoria, exclusiva y tener al menos 50 caracteres.'
        )
else:
    JWT_SIGNING_KEY = JWT_SIGNING_KEY or SECRET_KEY

SIMPLE_JWT = {
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': JWT_SIGNING_KEY,
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', '10'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '7'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

JWT_REFRESH_COOKIE = os.getenv('JWT_REFRESH_COOKIE', 'siminfra_refresh')
JWT_COOKIE_SECURE = env_bool('JWT_COOKIE_SECURE', not DEBUG)
JWT_COOKIE_SAMESITE = os.getenv('JWT_COOKIE_SAMESITE', 'Lax')
JWT_COOKIE_PATH = os.getenv('JWT_COOKIE_PATH', '/api/auth/')
PORTAL_IDLE_TIMEOUT_SECONDS = int(os.getenv('PORTAL_IDLE_TIMEOUT_SECONDS', '300'))
PORTAL_TRUSTED_PROXY_IPS = env_list('PORTAL_TRUSTED_PROXY_IPS', '127.0.0.1,::1')
PORTAL_WS_MAX_CONNECTIONS_PER_IP = int(os.getenv('PORTAL_WS_MAX_CONNECTIONS_PER_IP', '20'))
PORTAL_WS_MAX_CONNECTIONS_PER_USER = int(os.getenv('PORTAL_WS_MAX_CONNECTIONS_PER_USER', '5'))
PORTAL_WS_MESSAGES_PER_SECOND = int(os.getenv('PORTAL_WS_MESSAGES_PER_SECOND', '5'))
PORTAL_WS_MAX_MESSAGE_BYTES = int(os.getenv('PORTAL_WS_MAX_MESSAGE_BYTES', '16384'))
PORTAL_PAGE_SIZE = int(os.getenv('PORTAL_PAGE_SIZE', '50'))
PORTAL_MAX_PAGE_SIZE = int(os.getenv('PORTAL_MAX_PAGE_SIZE', '200'))
if PORTAL_PAGE_SIZE <= 0 or PORTAL_MAX_PAGE_SIZE < PORTAL_PAGE_SIZE:
    raise ImproperlyConfigured(
        'PORTAL_PAGE_SIZE debe ser positivo y no superar PORTAL_MAX_PAGE_SIZE.'
    )
if PORTAL_WS_MAX_MESSAGE_BYTES <= 0:
    raise ImproperlyConfigured('PORTAL_WS_MAX_MESSAGE_BYTES debe ser positivo.')

PORTAL_IMPORT_MAX_FILE_BYTES = int(os.getenv('PORTAL_IMPORT_MAX_FILE_BYTES', str(25 * 1024 * 1024)))
PORTAL_IMPORT_MAX_UNCOMPRESSED_BYTES = int(
    os.getenv('PORTAL_IMPORT_MAX_UNCOMPRESSED_BYTES', str(100 * 1024 * 1024))
)
PORTAL_IMPORT_MAX_ZIP_MEMBERS = int(os.getenv('PORTAL_IMPORT_MAX_ZIP_MEMBERS', '10000'))
PORTAL_IMPORT_MAX_ROWS = int(os.getenv('PORTAL_IMPORT_MAX_ROWS', '50000'))
PORTAL_IMPORT_MAX_COLUMNS = int(os.getenv('PORTAL_IMPORT_MAX_COLUMNS', '100'))
if min(
    PORTAL_IMPORT_MAX_FILE_BYTES,
    PORTAL_IMPORT_MAX_UNCOMPRESSED_BYTES,
    PORTAL_IMPORT_MAX_ZIP_MEMBERS,
    PORTAL_IMPORT_MAX_ROWS,
    PORTAL_IMPORT_MAX_COLUMNS,
) <= 0:
    raise ImproperlyConfigured('Los límites de importación XLSX deben ser positivos.')

DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE', str(2_621_440)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE', str(2_621_440)))
if DATA_UPLOAD_MAX_MEMORY_SIZE <= 0 or FILE_UPLOAD_MAX_MEMORY_SIZE <= 0:
    raise ImproperlyConfigured('Los límites de carga deben ser mayores que cero.')

FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY', '')
LEGACY_DJANGO_SECRET_KEY = os.getenv('LEGACY_DJANGO_SECRET_KEY', '')
if IS_PRODUCTION:
    require_env('FIELD_ENCRYPTION_KEY')
    try:
        Fernet(FIELD_ENCRYPTION_KEY.encode())
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            'FIELD_ENCRYPTION_KEY debe ser una clave Fernet válida.'
        ) from exc

SECURE_PROXY_SSL_HEADER = (
    ('HTTP_X_FORWARDED_PROTO', 'https')
    if env_bool('USE_X_FORWARDED_PROTO', IS_PRODUCTION)
    else None
)
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', IS_PRODUCTION)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', not DEBUG)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

if IS_PRODUCTION:
    insecure_settings = [
        name
        for name, value in {
            'SECURE_SSL_REDIRECT': SECURE_SSL_REDIRECT,
            'SESSION_COOKIE_SECURE': SESSION_COOKIE_SECURE,
            'CSRF_COOKIE_SECURE': CSRF_COOKIE_SECURE,
            'JWT_COOKIE_SECURE': JWT_COOKIE_SECURE,
        }.items()
        if not value
    ]
    if insecure_settings:
        raise ImproperlyConfigured(
            f'Configuración insegura en producción: {", ".join(insecure_settings)}.'
        )
    if SECURE_HSTS_SECONDS <= 0:
        raise ImproperlyConfigured('SECURE_HSTS_SECONDS debe ser mayor que cero en producción.')

LOG_FORMAT = os.getenv('DJANGO_LOG_FORMAT', 'json' if IS_PRODUCTION else 'simple').lower()
if LOG_FORMAT not in {'simple', 'json'}:
    raise ImproperlyConfigured('DJANGO_LOG_FORMAT debe ser simple o json.')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'request_id': {'()': 'config.logging_utils.RequestIdFilter'},
    },
    'formatters': {
        'simple': {
            'format': '{levelname} {name} [{request_id}]: {message}',
            'style': '{',
        },
        'json': {'()': 'config.logging_utils.JsonFormatter'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': LOG_FORMAT,
            'filters': ['request_id'],
        },
    },
    'root': {'handlers': ['console'], 'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO')},
    'loggers': {
        'portal.request': {
            'handlers': ['console'],
            'level': os.getenv(
                'DJANGO_REQUEST_LOG_LEVEL',
                'INFO' if IS_PRODUCTION else 'WARNING',
            ),
            'propagate': False,
        },
    },
}
