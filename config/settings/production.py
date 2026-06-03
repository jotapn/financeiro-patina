from .base import *

DEBUG = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

if not config('DATABASE_URL', default=''):
    DATABASES['default']['HOST'] = config('DB_HOST', default='pgbouncer')
    DATABASES['default']['PORT'] = config('DB_PORT', default='6432')
