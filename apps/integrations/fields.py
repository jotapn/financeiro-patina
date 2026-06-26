"""Campo de modelo com criptografia simétrica (Fernet).

Usado para guardar dados sensíveis de integração Open Finance (ex.: número de
conta mascarado) criptografados em repouso. A chave vem de
``settings.FIELD_ENCRYPTION_KEY`` (chave Fernet base64 de 32 bytes).
"""

from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


@lru_cache(maxsize=1)
def _get_fernet():
    from cryptography.fernet import Fernet

    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', '') or ''
    if not key:
        raise ImproperlyConfigured(
            'FIELD_ENCRYPTION_KEY não configurada. Gere uma chave Fernet e defina no .env.'
        )
    if isinstance(key, str):
        key = key.encode('utf-8')
    try:
        return Fernet(key)
    except Exception as exc:  # chave malformada
        raise ImproperlyConfigured(f'FIELD_ENCRYPTION_KEY inválida: {exc}') from exc


def encrypt_value(value: str) -> str:
    if value is None or value == '':
        return value
    token = _get_fernet().encrypt(str(value).encode('utf-8'))
    return token.decode('utf-8')


def decrypt_value(token: str) -> str:
    if token is None or token == '':
        return token
    from cryptography.fernet import InvalidToken

    try:
        return _get_fernet().decrypt(str(token).encode('utf-8')).decode('utf-8')
    except InvalidToken:
        # Valor não criptografado (ex.: dados legados) — retorna como está.
        return token


class EncryptedTextField(models.TextField):
    """TextField que criptografa o valor antes de persistir no banco."""

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt_value(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == '':
            return value
        return encrypt_value(value)
