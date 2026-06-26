"""Lógica de sincronização Open Finance (Pluggy).

Responsável por:
- criar/atualizar os vínculos de conta (``PluggyAccountLink``) a partir dos
  *accounts* retornados pelo Pluggy;
- importar transações de forma **idempotente** (deduplicadas por ``external_id``);
- reconciliar o saldo da conta interna com o saldo reportado pelo Pluggy.

MVP: apenas contas bancárias (``BANK``). Cartão de crédito (``CREDIT``) é Fase 2.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction as db_transaction
from django.utils import timezone

from .client import PluggyClient
from .models import PluggyAccountLink, PluggyItem

logger = logging.getLogger(__name__)

# Mapeia (parte de) categorias do Pluggy para nomes de categorias internas.
# A correspondência é por substring normalizada; se nada casar, usa o fallback.
PLUGGY_CATEGORY_HINTS = {
    'food': 'Alimentação',
    'restaurant': 'Alimentação',
    'aliment': 'Alimentação',
    'supermarket': 'Alimentação',
    'transport': 'Transporte',
    'travel': 'Transporte',
    'uber': 'Transporte',
    'health': 'Saúde',
    'saúde': 'Saúde',
    'education': 'Educação',
    'shopping': 'Compras',
    'leisure': 'Lazer',
    'entertain': 'Lazer',
    'house': 'Moradia',
    'rent': 'Moradia',
    'utilit': 'Moradia',
    'salary': 'Salário',
    'income': 'Salário',
    'investment': 'Investimentos',
}

FALLBACK_CATEGORY_NAME = 'Open Finance'


def _normalize(value):
    return (value or '').strip().lower()


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


def _parse_date(value):
    if not value:
        return timezone.localdate()
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).date()
    except ValueError:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()


def resolve_category(family_group, transaction_type, pluggy_category=None):
    """Resolve uma ``Category`` válida (obrigatória/PROTECT) para a transação.

    Tenta casar a categoria do Pluggy com uma categoria existente da família (ou
    de sistema); caso contrário, usa/cria uma categoria de fallback.
    """
    from apps.categories.models import Category

    cat_type = 'income' if transaction_type == 'income' else 'expense'
    available = list(
        Category.objects.filter(category_type=cat_type).filter(
            models_q_family(family_group)
        )
    )

    norm_pluggy = _normalize(pluggy_category)
    if norm_pluggy:
        target_name = None
        for hint, name in PLUGGY_CATEGORY_HINTS.items():
            if hint in norm_pluggy:
                target_name = _normalize(name)
                break
        # 1) match direto pelo nome do Pluggy; 2) match pelo nome mapeado.
        for cat in available:
            cname = _normalize(cat.name)
            if cname == norm_pluggy or (target_name and cname == target_name):
                return cat

    fallback = next(
        (c for c in available if _normalize(c.name) == _normalize(FALLBACK_CATEGORY_NAME)),
        None,
    )
    if fallback:
        return fallback
    return Category.objects.create(
        family_group=family_group,
        name=FALLBACK_CATEGORY_NAME,
        category_type=cat_type,
        icon='git-branch',
        is_system=False,
    )


def models_q_family(family_group):
    """Filtro: categorias da família OU categorias de sistema (family_group nulo)."""
    from django.db.models import Q

    return Q(family_group=family_group) | Q(family_group__isnull=True)


def sync_account_links(item: PluggyItem, client: PluggyClient):
    """Cria/atualiza ``PluggyAccountLink`` a partir dos accounts do item.

    Usado tanto no fluxo de confirmação (para listar contas detectadas) quanto
    no sync periódico. Não decide mapeamento — apenas reflete o que o Pluggy expõe.
    """
    accounts = client.list_accounts(item.pluggy_item_id)
    seen_ids = []
    for acc in accounts:
        acc_id = acc.get('id')
        if not acc_id:
            continue
        seen_ids.append(acc_id)
        number = acc.get('number') or acc.get('marketingName') or ''
        PluggyAccountLink.objects.update_or_create(
            pluggy_account_id=acc_id,
            defaults={
                'item': item,
                'pluggy_type': (acc.get('type') or 'BANK').upper(),
                'pluggy_subtype': acc.get('subtype') or '',
                'name': acc.get('name') or acc.get('marketingName') or 'Conta',
                'number_masked': str(number)[-8:] if number else '',
                'pluggy_balance': _to_decimal(acc.get('balance')),
                'currency_code': acc.get('currencyCode') or 'BRL',
            },
        )
    return PluggyAccountLink.objects.filter(item=item, pluggy_account_id__in=seen_ids)


def _import_transactions_for_link(link: PluggyAccountLink, client: PluggyClient):
    """Importa transações de um vínculo BANK já mapeado. Retorna nº de criadas."""
    from apps.transactions.models import Transaction

    account = link.financial_account
    if account is None:
        return 0

    # v2 não filtra por data de transação; na 1ª sync trazemos tudo e cortamos por
    # data no cliente; nas incrementais usamos createdAtFrom (data de ingestão).
    cutoff = None
    if link.last_synced_at:
        created_from = (link.last_synced_at - timedelta(days=2)).date().isoformat()
    else:
        created_from = None
        days = getattr(settings, 'PLUGGY_INITIAL_SYNC_DAYS', 90)
        cutoff = timezone.localdate() - timedelta(days=days)

    txns = client.list_transactions(link.pluggy_account_id, created_from=created_from)
    created = 0
    family_group = account.family_group

    for txn in txns:
        external_id = txn.get('id')
        if not external_id:
            continue
        txn_date = _parse_date(txn.get('date'))
        if cutoff and txn_date < cutoff:
            continue
        if Transaction.objects.filter(
            family_group=family_group,
            external_source=Transaction.SOURCE_PLUGGY,
            external_id=external_id,
        ).exists():
            continue

        raw_amount = _to_decimal(txn.get('amount'))
        # Direção pelo campo `type` (inequívoco): DEBIT = saída, CREDIT = entrada.
        # O sinal de `amount` é fallback raro quando `type` não vem preenchido.
        raw_type = (txn.get('type') or '').upper()
        if raw_type == 'DEBIT':
            txn_type = 'expense'
        elif raw_type == 'CREDIT':
            txn_type = 'income'
        else:
            txn_type = 'income' if raw_amount < 0 else 'expense'
        amount = abs(raw_amount)
        if amount == 0:
            continue

        pluggy_category = txn.get('category')
        category = resolve_category(family_group, txn_type, pluggy_category)
        notes = f'Pluggy: {pluggy_category}' if pluggy_category else ''
        try:
            with db_transaction.atomic():
                Transaction.objects.create(
                    user=account.owner,
                    family_group=family_group,
                    account=account,
                    category=category,
                    description=(txn.get('description') or 'Transação importada')[:255],
                    amount=amount,
                    transaction_type=txn_type,
                    date=txn_date,
                    status='paid',
                    notes=notes,
                    external_source=Transaction.SOURCE_PLUGGY,
                    external_id=external_id,
                    is_auto_imported=True,
                )
            created += 1
        except IntegrityError:
            # Corrida com a constraint única — já importada por outro worker.
            continue

    return created


def _reconcile_balance(link: PluggyAccountLink):
    """Ajusta ``initial_balance`` para o saldo computado bater com o Pluggy."""
    from apps.accounts.models import FinancialAccount

    if link.pluggy_balance is None or link.financial_account_id is None:
        return
    account = FinancialAccount.objects.with_current_balance().get(pk=link.financial_account_id)
    delta = link.pluggy_balance - account.current_balance
    if delta != 0:
        account.initial_balance = account.initial_balance + delta
        account.save(update_fields=['initial_balance'])


def sync_item(item: PluggyItem, client: PluggyClient = None):
    """Sincroniza um item: atualiza accounts, importa transações e reconcilia saldo."""
    client = client or PluggyClient()
    summary = {'links': 0, 'imported': 0}

    try:
        remote = client.get_item(item.pluggy_item_id)
        # Pluggy retorna status em maiúsculas (UPDATED, LOGIN_ERROR, ...); normalizamos.
        item.status = (remote.get('status') or '').lower() or item.status
        item.connector_name = (remote.get('connector') or {}).get('name', item.connector_name)
    except Exception as exc:  # noqa: BLE001 — registra mas segue tentando os accounts
        logger.warning('Não foi possível ler item %s: %s', item.pluggy_item_id, exc)

    links = sync_account_links(item, client)
    summary['links'] = links.count()

    for link in links.filter(
        pluggy_type=PluggyAccountLink.TYPE_BANK,
        is_active=True,
        link_mode__in=[PluggyAccountLink.MODE_CREATED, PluggyAccountLink.MODE_MAPPED],
        financial_account__isnull=False,
    ):
        try:
            summary['imported'] += _import_transactions_for_link(link, client)
            _reconcile_balance(link)
            link.last_synced_at = timezone.now()
            link.save(update_fields=['last_synced_at'])
        except Exception as exc:  # noqa: BLE001
            logger.error('Erro ao sincronizar vínculo %s: %s', link.pk, exc)

    item.last_synced_at = timezone.now()
    item.error_message = ''
    item.save(update_fields=['status', 'connector_name', 'last_synced_at', 'error_message'])
    return summary
