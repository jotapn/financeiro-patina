"""Cliente HTTP para a API do Pluggy (Open Finance).

Segue o mesmo padrão de chamadas externas usado em ``apps/investments/tasks.py``
(httpx com timeout, ``raise_for_status()`` e ``.json()``). A API Key do Pluggy é
obtida a partir do ``clientId``/``clientSecret`` e cacheada no Redis (~110 min,
abaixo do TTL de 2h da chave).
"""

import logging

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

API_KEY_CACHE_KEY = 'pluggy:api_key'
API_KEY_CACHE_TTL = 110 * 60  # 110 minutos
DEFAULT_TIMEOUT = 20


class PluggyError(Exception):
    """Erro genérico ao falar com a API do Pluggy."""


class PluggyClient:
    def __init__(self, client_id=None, client_secret=None, base_url=None):
        self.client_id = client_id or settings.PLUGGY_CLIENT_ID
        self.client_secret = client_secret or settings.PLUGGY_CLIENT_SECRET
        self.base_url = (base_url or settings.PLUGGY_API_URL).rstrip('/')
        if not self.client_id or not self.client_secret:
            raise PluggyError('PLUGGY_CLIENT_ID/PLUGGY_CLIENT_SECRET não configurados.')

    # ------------------------------------------------------------------ auth
    def _fetch_api_key(self):
        resp = httpx.post(
            f'{self.base_url}/auth',
            json={'clientId': self.client_id, 'clientSecret': self.client_secret},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        api_key = resp.json().get('apiKey')
        if not api_key:
            raise PluggyError('Resposta de /auth sem apiKey.')
        return api_key

    def get_api_key(self, force_refresh=False):
        if not force_refresh:
            cached = cache.get(API_KEY_CACHE_KEY)
            if cached:
                return cached
        api_key = self._fetch_api_key()
        cache.set(API_KEY_CACHE_KEY, api_key, timeout=API_KEY_CACHE_TTL)
        return api_key

    def _headers(self, api_key=None):
        return {'X-API-KEY': api_key or self.get_api_key()}

    def _request(self, method, path, *, params=None, json=None):
        url = f'{self.base_url}{path}'
        api_key = self.get_api_key()
        try:
            resp = httpx.request(
                method, url, headers=self._headers(api_key), params=params, json=json, timeout=DEFAULT_TIMEOUT
            )
            if resp.status_code in (401, 403):
                # Chave expirada/inválida: renova uma vez e tenta de novo.
                api_key = self.get_api_key(force_refresh=True)
                resp = httpx.request(
                    method, url, headers=self._headers(api_key), params=params, json=json, timeout=DEFAULT_TIMEOUT
                )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.error('Erro Pluggy %s %s: %s', method, path, exc)
            raise PluggyError(str(exc)) from exc

    # -------------------------------------------------------------- connect
    def create_connect_token(self, item_id=None, client_user_id=None, options=None):
        """Gera um connect token de curta duração para o widget Pluggy Connect.

        ``client_user_id`` (ex.: e-mail do usuário) dá rastreabilidade ponta-a-ponta
        da conexão. Todos esses campos vão dentro de ``options`` conforme a API Pluggy.
        """
        payload = {}
        if item_id:
            payload['itemId'] = item_id
        opts = dict(options or {})
        if client_user_id:
            opts['clientUserId'] = client_user_id
        if settings.PLUGGY_WEBHOOK_URL:
            opts['webhookUrl'] = settings.PLUGGY_WEBHOOK_URL
        # Evita criar um item duplicado ao reconectar o mesmo banco/credenciais.
        opts.setdefault('avoidDuplicates', True)
        payload['options'] = opts
        data = self._request('POST', '/connect_token', json=payload)
        return data.get('accessToken')

    # ------------------------------------------------------------- recursos
    def get_item(self, item_id):
        return self._request('GET', f'/items/{item_id}')

    def list_accounts(self, item_id):
        data = self._request('GET', '/accounts', params={'itemId': item_id})
        return data.get('results', [])

    def list_transactions(self, account_id, created_from=None):
        """Lista transações via ``GET /v2/transactions`` (paginação por cursor).

        A v1 (``/transactions`` com page/pageSize) foi descontinuada (HTTP 410). A v2
        retorna ``{results, next}`` e usa um cursor opaco em ``next`` para a próxima
        página. ``created_from`` (YYYY-MM-DD) filtra por data de ingestão no Pluggy,
        útil para sincronizações incrementais.
        """
        results = []
        base_params = {'accountId': account_id}
        if created_from:
            base_params['createdAtFrom'] = created_from
        cursor = None
        for _ in range(500):  # guarda contra loop infinito
            params = dict(base_params)
            if cursor:
                params['cursor'] = cursor
            data = self._request('GET', '/v2/transactions', params=params)
            results.extend(data.get('results', []))
            nxt = data.get('next')
            if not nxt:
                break
            cursor = self._extract_cursor(nxt)
            if not cursor:
                break
        return results

    @staticmethod
    def _extract_cursor(nxt):
        """Aceita tanto um token de cursor quanto uma URL completa em ``next``."""
        nxt = str(nxt)
        if nxt.startswith('http'):
            from urllib.parse import parse_qs, urlparse

            return (parse_qs(urlparse(nxt).query).get('cursor') or [None])[0]
        return nxt

    # ---------------------------------------------------------- fase 2 stub
    def list_credit_card_bills(self, account_id):
        """Faturas de cartão de crédito (Fase 2)."""
        data = self._request('GET', '/bills', params={'accountId': account_id})
        return data.get('results', [])

    def delete_item(self, item_id):
        try:
            return self._request('DELETE', f'/items/{item_id}')
        except PluggyError:
            # Item pode já ter sido removido no lado do Pluggy.
            return None
