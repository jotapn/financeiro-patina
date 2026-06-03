from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

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


SECRET_KEY = config('SECRET_KEY')
DEBUG = _get_bool_env('DEBUG', default=False)
ALLOWED_HOSTS = [host.strip() for host in config('ALLOWED_HOSTS', default='localhost').split(',') if host.strip()]

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
    'apps.core',
    'apps.accounts',
    'apps.transactions',
    'apps.cards',
    'apps.investments',
    'apps.categories',
    'apps.budgets',
    'apps.reports',
    'apps.ai_assistant',
    'apps.notifications',
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

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
    }
}



