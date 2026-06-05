from .base import *
from .base import _get_bool_env

from django.core.exceptions import ImproperlyConfigured

DEBUG = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = _get_bool_env('SECURE_SSL_REDIRECT', default=True)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = _get_bool_env('SESSION_COOKIE_SECURE', default=True)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=1209600, cast=int)
CSRF_COOKIE_SECURE = _get_bool_env('CSRF_COOKIE_SECURE', default=True)
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

_allowed_hosts_env = config('ALLOWED_HOSTS', default='').strip()
if not _allowed_hosts_env:
    raise ImproperlyConfigured('ALLOWED_HOSTS must be set explicitly in production.')
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts_env.split(',') if host.strip()]
if '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS cannot contain "*" in production.')

if not config('DATABASE_URL', default=''):
    DATABASES['default']['HOST'] = config('DB_HOST', default='pgbouncer')
    DATABASES['default']['PORT'] = config('DB_PORT', default='6432')
