import base64
import hashlib
from functools import wraps
from io import BytesIO
from pathlib import PurePath

import qrcode
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import SecurityEvent

SENSITIVE_METADATA_KEYS = {'password', 'password1', 'password2', 'token', 'secret', 'key'}
SUSPICIOUS_FILENAME_PARTS = ('..', '/', '\\', '\x00', ':')


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or None


def safe_next_url(request, value, fallback='dashboard'):
    if value and url_has_allowed_host_and_scheme(
        value,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return value
    return reverse(fallback)


def _hash_value(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:32]


def hash_identifier(value):
    return _hash_value(str(value).strip().lower())


def _rate_identity(request, identifier=None):
    user = getattr(request, 'user', None)
    if identifier:
        identity = str(identifier).strip().lower()
    elif user and user.is_authenticated:
        identity = f'user:{user.pk}'
    else:
        identity = 'anonymous'
    return f'{identity}:ip:{get_client_ip(request) or "unknown"}'


def is_rate_limited(scope, request, *, limit, window, identifier=None):
    identity = _hash_value(_rate_identity(request, identifier))
    key = f'rate_limit:{scope}:{identity}'
    added = cache.add(key, 1, timeout=window)
    if added:
        return False
    try:
        current = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        return False
    return current > limit


def rate_limit_post(scope, *, limit_setting='RATE_LIMIT_CRITICAL_POST_LIMIT', window_setting='RATE_LIMIT_CRITICAL_POST_WINDOW'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method == 'POST':
                if is_rate_limited(
                    scope,
                    request,
                    limit=getattr(settings, limit_setting),
                    window=getattr(settings, window_setting),
                ):
                    audit_security_event(
                        request,
                        SecurityEvent.RATE_LIMITED,
                        metadata={'scope': scope},
                    )
                    if getattr(request, 'htmx', False):
                        return HttpResponse('Muitas tentativas. Tente novamente em instantes.', status=429)
                    messages.error(request, 'Muitas tentativas. Tente novamente em instantes.')
                    return redirect(request.META.get('HTTP_REFERER') or 'dashboard')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def _sanitize_metadata(metadata):
    sanitized = {}
    for key, value in (metadata or {}).items():
        if key in SENSITIVE_METADATA_KEYS:
            continue
        sanitized[key] = str(value)[:200]
    return sanitized


def audit_security_event(request, event_type, *, user=None, metadata=None):
    event_user = user or getattr(request, 'user', None)
    if event_user and not event_user.is_authenticated:
        event_user = None
    SecurityEvent.objects.create(
        user=event_user,
        event_type=event_type,
        ip_address=get_client_ip(request),
        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:255],
        metadata=_sanitize_metadata(metadata),
    )


def validate_upload_file(uploaded_file):
    if not uploaded_file:
        return

    original_name = uploaded_file.name or ''
    safe_name = PurePath(original_name).name
    if safe_name != original_name or any(part in original_name for part in SUSPICIOUS_FILENAME_PARTS):
        raise ValidationError('Nome de arquivo invalido.')

    extension = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''
    allowed_extensions = {ext.strip().lower().lstrip('.') for ext in settings.ALLOWED_UPLOAD_EXTENSIONS}
    if extension not in allowed_extensions:
        raise ValidationError('Tipo de arquivo nao permitido.')

    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
    allowed_mimes = {mime.strip().lower() for mime in settings.ALLOWED_UPLOAD_MIME_TYPES}
    if content_type not in allowed_mimes:
        raise ValidationError('Tipo de arquivo nao permitido.')

    if uploaded_file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError(f'Arquivo maior que {settings.MAX_UPLOAD_SIZE_MB} MB.')


def confirmed_totp_device(user):
    if not user or not user.is_authenticated:
        return None
    return TOTPDevice.objects.filter(user=user, confirmed=True).order_by('id').first()


def has_confirmed_totp(user):
    return confirmed_totp_device(user) is not None


def user_must_configure_2fa(user):
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser) and not has_confirmed_totp(user))


def user_requires_2fa(user):
    return bool(user and user.is_authenticated and ((user.is_staff or user.is_superuser) or has_confirmed_totp(user)))


def user_is_otp_verified(user):
    is_verified = getattr(user, 'is_verified', None)
    return bool(is_verified and is_verified())


def user_needs_2fa(user):
    return user_requires_2fa(user) and not user_is_otp_verified(user)


def get_setup_totp_device(user):
    device = TOTPDevice.objects.filter(user=user, confirmed=False).order_by('-id').first()
    if device is None:
        device = TOTPDevice.objects.create(user=user, name='default', confirmed=False)
    return device


def build_qr_code_data_url(device):
    image = qrcode.make(device.config_url)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def verify_and_login_otp(request, device, token):
    if device and device.verify_token(token):
        otp_login(request, device)
        return True
    return False
