import json

import httpx
import psutil
from django.conf import settings
from langchain_community.llms import Ollama

MODEL_PRIORITY = [
    'llama3.1:8b-instruct-q4_K_M',
    'mistral:7b-instruct-q4_K_M',
    'gemma2:2b-instruct',
]


def get_best_model() -> str:
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    if ram_gb >= 16:
        return MODEL_PRIORITY[0]
    if ram_gb >= 8:
        return MODEL_PRIORITY[1]
    return MODEL_PRIORITY[2]


def _candidate_base_urls():
    configured = getattr(settings, 'OLLAMA_BASE_URL', 'http://ollama:11434')
    candidates = [configured]
    if 'localhost' not in configured:
        candidates.append('http://localhost:11434')
    if '127.0.0.1' not in configured:
        candidates.append('http://127.0.0.1:11434')
    seen = set()
    return [url for url in candidates if not (url in seen or seen.add(url))]


def _get_models_from_url(base_url: str):
    with httpx.Client(timeout=5) as client:
        response = client.get(f'{base_url}/api/tags')
        response.raise_for_status()
        payload = response.json()
    return [item.get('name', '') for item in payload.get('models', []) if item.get('name')]


def get_ollama_connection():
    errors = []
    for base_url in _candidate_base_urls():
        try:
            return base_url, _get_models_from_url(base_url), None
        except Exception as exc:
            errors.append(f'{base_url}: {exc}')
    return None, [], '; '.join(errors)


def resolve_model():
    preferred = get_best_model()
    base_url, installed_models, error = get_ollama_connection()
    if not base_url:
        return {
            'base_url': None,
            'preferred_model': preferred,
            'model': preferred,
            'installed_models': installed_models,
            'status': 'offline',
            'error': error or 'Ollama indisponível.',
        }

    if preferred in installed_models:
        chosen = preferred
    else:
        chosen = next((name for name in MODEL_PRIORITY if name in installed_models), None)
        if not chosen:
            chosen = installed_models[0] if installed_models else preferred

    status = 'online'
    if chosen != preferred:
        status = 'fallback'

    return {
        'base_url': base_url,
        'preferred_model': preferred,
        'model': chosen,
        'installed_models': installed_models,
        'status': status,
        'error': '',
    }


def get_llm(streaming=True):
    resolved = resolve_model()
    if not resolved['base_url']:
        raise RuntimeError(resolved['error'] or 'Ollama indisponível.')
    return Ollama(
        model=resolved['model'],
        base_url=resolved['base_url'],
        temperature=0.3,
        top_p=0.9,
    )


def pull_model():
    resolved = resolve_model()
    base_url = resolved['base_url'] or _candidate_base_urls()[0]
    preferred = resolved['preferred_model']
    with httpx.Client(timeout=1200) as client:
        response = client.post(f'{base_url}/api/pull', json={'name': preferred})
        response.raise_for_status()
        updates = []
        for line in response.text.splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get('status'):
                updates.append(payload['status'])
    return preferred, updates
