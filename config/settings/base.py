from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import sys

try:
    from decouple import config as decouple_config
except ImportError:
    decouple_config = None

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_UNSET = object()
_DOTENV_CACHE = None


def _dotenv_values():
    global _DOTENV_CACHE
    if _DOTENV_CACHE is not None:
        return _DOTENV_CACHE
    values = {}
    env_path = BASE_DIR / '.env'
    if env_path.exists():
        for raw_line in env_path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    _DOTENV_CACHE = values
    return values


def config(name, default=_UNSET, cast=None):
    if decouple_config is not None:
        kwargs = {}
        if default is not _UNSET:
            kwargs['default'] = default
        if cast is not None:
            kwargs['cast'] = cast
        return decouple_config(name, **kwargs)

    import os

    if name in os.environ:
        value = os.environ[name]
    else:
        values = _dotenv_values()
        if name in values:
            value = values[name]
        elif default is not _UNSET:
            value = default
        else:
            raise RuntimeError(f'Missing required environment variable: {name}')

    if cast is None:
        return value
    return cast(value)

def _get_bool_env(name: str, default: bool = False) -> bool:
    value = config(name, default=str(default))
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 't', 'yes', 'y', 'on'}:
        return True
    if normalized in {'0', 'false', 'f', 'no', 'n', 'off'}:
        return False
    return default


def _get_csv_env(name: str, default: str = '') -> list[str]:
    return [item.strip() for item in config(name, default=default).split(',') if item.strip()]


SECRET_KEY = config('SECRET_KEY')
DEBUG = _get_bool_env('DEBUG', default=False)
ALLOWED_HOSTS = _get_csv_env('ALLOWED_HOSTS', default='localhost')
CSRF_TRUSTED_ORIGINS = _get_csv_env('CSRF_TRUSTED_ORIGINS')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'django_filters',
    'django_htmx',
    'django_celery_beat',
    'channels',
    'django_otp',
    'django_otp.plugins.otp_totp',
]

LOCAL_APPS = [
    'apps.core.apps.CoreConfig',
    'apps.accounts',
    'apps.transactions',
    'apps.cards',
    'apps.investments',
    'apps.categories',
    'apps.budgets',
    'apps.reports',
    'apps.ai_assistant',
    'apps.notifications',
    'apps.integrations',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.middleware.EnsureUserProfileMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'apps.core.middleware.RequireTwoFactorMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='financeflow'),
        'USER': config('DB_USER', default='financeflow'),
        'PASSWORD': config('DB_PASSWORD', default='financeflow123'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

database_url = config('DATABASE_URL', default='')
if database_url:
    parsed = urlparse(database_url)
    query = parse_qs(parsed.query)
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/') or config('DB_NAME', default='financeflow'),
        'USER': unquote(parsed.username or config('DB_USER', default='financeflow')),
        'PASSWORD': unquote(parsed.password or config('DB_PASSWORD', default='financeflow123')),
        'HOST': parsed.hostname or config('DB_HOST', default='localhost'),
        'PORT': str(parsed.port or config('DB_PORT', default='5432')),
        'OPTIONS': {
            'sslmode': query.get('sslmode', [config('DB_SSLMODE', default='require')])[0],
        },
    }

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [config('REDIS_URL', default='redis://redis:6379/0')]},
    }
}

CELERY_BROKER_URL = config(
    'CELERY_BROKER_URL',
    default=config('REDIS_URL', default='redis://redis:6379/0'),
)
CELERY_RESULT_BACKEND = config(
    'CELERY_RESULT_BACKEND',
    default=config('REDIS_URL', default='redis://redis:6379/0'),
)
CELERY_TASK_DEFAULT_QUEUE = config('CELERY_TASK_DEFAULT_QUEUE', default='default')
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TIMEZONE = 'America/Sao_Paulo'

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = _get_bool_env('EMAIL_USE_TLS', default=False)
EMAIL_USE_SSL = _get_bool_env('EMAIL_USE_SSL', default=False)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='FinanceFlow <no-reply@localhost>')
PASSWORD_RESET_TIMEOUT = config('PASSWORD_RESET_TIMEOUT', default=259200, cast=int)

AUTH_USER_MODEL = 'core.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'
OTP_TOTP_ISSUER = config('OTP_TOTP_ISSUER', default='FinanceFlow')

MAX_UPLOAD_SIZE_MB = config('MAX_UPLOAD_SIZE_MB', default=5, cast=int)
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = config(
    'ALLOWED_UPLOAD_EXTENSIONS',
    default='jpg,jpeg,png,pdf',
)
ALLOWED_UPLOAD_EXTENSIONS = [ext.strip() for ext in ALLOWED_UPLOAD_EXTENSIONS.split(',') if ext.strip()]
ALLOWED_UPLOAD_MIME_TYPES = config(
    'ALLOWED_UPLOAD_MIME_TYPES',
    default='image/jpeg,image/png,application/pdf',
)
ALLOWED_UPLOAD_MIME_TYPES = [mime.strip() for mime in ALLOWED_UPLOAD_MIME_TYPES.split(',') if mime.strip()]

RATE_LIMIT_DEFAULT_LIMIT = config('RATE_LIMIT_DEFAULT_LIMIT', default=30, cast=int)
RATE_LIMIT_DEFAULT_WINDOW = config('RATE_LIMIT_DEFAULT_WINDOW', default=60, cast=int)
RATE_LIMIT_LOGIN_LIMIT = config('RATE_LIMIT_LOGIN_LIMIT', default=5, cast=int)
RATE_LIMIT_LOGIN_WINDOW = config('RATE_LIMIT_LOGIN_WINDOW', default=300, cast=int)
RATE_LIMIT_REGISTER_LIMIT = config('RATE_LIMIT_REGISTER_LIMIT', default=5, cast=int)
RATE_LIMIT_REGISTER_WINDOW = config('RATE_LIMIT_REGISTER_WINDOW', default=600, cast=int)
RATE_LIMIT_2FA_LIMIT = config('RATE_LIMIT_2FA_LIMIT', default=5, cast=int)
RATE_LIMIT_2FA_WINDOW = config('RATE_LIMIT_2FA_WINDOW', default=300, cast=int)
RATE_LIMIT_PASSWORD_RESET_LIMIT = config('RATE_LIMIT_PASSWORD_RESET_LIMIT', default=5, cast=int)
RATE_LIMIT_PASSWORD_RESET_WINDOW = config('RATE_LIMIT_PASSWORD_RESET_WINDOW', default=600, cast=int)
RATE_LIMIT_CRITICAL_POST_LIMIT = config('RATE_LIMIT_CRITICAL_POST_LIMIT', default=20, cast=int)
RATE_LIMIT_CRITICAL_POST_WINDOW = config('RATE_LIMIT_CRITICAL_POST_WINDOW', default=60, cast=int)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
    }
}

# Open Finance / Pluggy
PLUGGY_CLIENT_ID = config('PLUGGY_CLIENT_ID', default='')
PLUGGY_CLIENT_SECRET = config('PLUGGY_CLIENT_SECRET', default='')
PLUGGY_API_URL = config('PLUGGY_API_URL', default='https://api.pluggy.ai')
PLUGGY_USE_SANDBOX = _get_bool_env('PLUGGY_USE_SANDBOX', default=True)
PLUGGY_WEBHOOK_URL = config('PLUGGY_WEBHOOK_URL', default='')
# Segredo compartilhado: o webhook só é aceito com ?token=<este valor>.
PLUGGY_WEBHOOK_SECRET = config('PLUGGY_WEBHOOK_SECRET', default='')
# Janela (em dias) para a primeira importação de transações de uma conta.
PLUGGY_INITIAL_SYNC_DAYS = config('PLUGGY_INITIAL_SYNC_DAYS', default=90, cast=int)
# Chave Fernet (base64, 32 bytes) usada para criptografar dados sensíveis de integração.
# Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default='')

if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
    CACHES['default'] = {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'financeflow-tests',
    }
    CHANNEL_LAYERS['default'] = {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }



