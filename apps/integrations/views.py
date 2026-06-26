import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.decorators import family_edit_required
from apps.core.models import SecurityEvent
from apps.core.security import audit_security_event, rate_limit_post

from .client import PluggyClient, PluggyError
from .models import PluggyAccountLink, PluggyItem
from .services import sync_account_links
from .tasks import sync_pluggy_item

logger = logging.getLogger(__name__)


@login_required
def pluggy_list(request):
    group = request.user.profile.family_group
    items = (
        PluggyItem.objects.filter(family_group=group, is_active=True)
        .prefetch_related('account_links')
        .order_by('-created_at')
    )
    return render(request, 'integrations/pluggy/list.html', {'items': items})


@login_required
@family_edit_required
def pluggy_connect(request):
    """Renderiza o widget Pluggy Connect com um connect token recém-gerado."""
    connect_token = None
    error = None
    try:
        connect_token = PluggyClient().create_connect_token(client_user_id=request.user.email)
    except PluggyError as exc:
        error = str(exc)
        logger.error('Falha ao gerar connect token: %s', exc)
    return render(
        request,
        'integrations/pluggy/connect.html',
        {
            'connect_token': connect_token,
            'error': error,
            'use_sandbox': settings.PLUGGY_USE_SANDBOX,
        },
    )


@login_required
@family_edit_required
@rate_limit_post('pluggy_callback')
@require_POST
def pluggy_callback(request):
    """Recebe o ``itemId`` do widget (onSuccess), cria o item e busca as contas."""
    item_id = request.POST.get('item_id') or ''
    if not item_id:
        return HttpResponseBadRequest('item_id ausente')

    group = request.user.profile.family_group
    client = PluggyClient()
    try:
        remote = client.get_item(item_id)
    except PluggyError as exc:
        messages.error(request, f'Não foi possível ler a conexão no Pluggy: {exc}')
        return redirect('pluggy_list')

    connector = remote.get('connector') or {}
    item, _ = PluggyItem.objects.update_or_create(
        pluggy_item_id=item_id,
        defaults={
            'family_group': group,
            'owner': request.user,
            'connector_id': connector.get('id'),
            'connector_name': connector.get('name', ''),
            'connector_image_url': connector.get('imageUrl', '') or '',
            'status': (remote.get('status') or '').lower() or PluggyItem.STATUS_UPDATED,
            'is_active': True,
        },
    )
    try:
        sync_account_links(item, client)
    except PluggyError as exc:
        messages.error(request, f'Conexão criada, mas falhou ao listar contas: {exc}')
        return redirect('pluggy_list')

    audit_security_event(
        request,
        SecurityEvent.PROFILE_CHANGED,
        metadata={'action': 'pluggy_connected', 'connector': item.connector_name},
    )
    return redirect('pluggy_confirm', item_pk=item.pk)


@login_required
@family_edit_required
@rate_limit_post('pluggy_confirm')
def pluggy_confirm(request, item_pk):
    """Tela híbrida: criar nova conta, vincular a existente ou ignorar cada account."""
    group = request.user.profile.family_group
    item = get_object_or_404(PluggyItem, pk=item_pk, family_group=group, is_active=True)
    # MVP: somente contas bancárias.
    links = item.account_links.filter(pluggy_type=PluggyAccountLink.TYPE_BANK)

    if request.method == 'POST':
        _apply_mapping(request, group, links)
        messages.success(request, 'Contas vinculadas! Iniciando importação...')
        sync_pluggy_item.delay(item.pk)
        return redirect('pluggy_list')

    from apps.accounts.models import FinancialAccount

    existing_accounts = FinancialAccount.objects.filter(family_group=group, is_active=True).order_by('name')
    credit_links = item.account_links.filter(pluggy_type=PluggyAccountLink.TYPE_CREDIT)
    return render(
        request,
        'integrations/pluggy/confirm.html',
        {
            'item': item,
            'links': links,
            'credit_links': credit_links,
            'existing_accounts': existing_accounts,
        },
    )


def _apply_mapping(request, group, links):
    """Processa o POST da tela de confirmação criando/vinculando cada conta."""
    from apps.accounts.models import FinancialAccount

    for link in links:
        action = request.POST.get(f'action_{link.pk}', 'ignore')

        if action == 'create':
            account = FinancialAccount.objects.create(
                owner=request.user,
                family_group=group,
                name=(request.POST.get(f'name_{link.pk}') or link.name or 'Conta importada')[:100],
                account_type='checking',
                bank='other',
                bank_custom=link.item.connector_name[:100],
                initial_balance=0,
                ownership='shared' if request.user.profile.family_group else 'personal',
            )
            link.financial_account = account
            link.link_mode = PluggyAccountLink.MODE_CREATED

        elif action == 'map':
            account_id = request.POST.get(f'account_{link.pk}')
            account = FinancialAccount.objects.filter(
                pk=account_id, family_group=group, is_active=True
            ).first()
            if account:
                link.financial_account = account
                link.link_mode = PluggyAccountLink.MODE_MAPPED
            else:
                link.link_mode = PluggyAccountLink.MODE_IGNORED
        else:
            link.financial_account = None
            link.link_mode = PluggyAccountLink.MODE_IGNORED

        link.save(update_fields=['financial_account', 'link_mode', 'updated_at'])


@login_required
@family_edit_required
@rate_limit_post('pluggy_sync')
@require_POST
def pluggy_sync_now(request, item_pk):
    group = request.user.profile.family_group
    item = get_object_or_404(PluggyItem, pk=item_pk, family_group=group, is_active=True)
    sync_pluggy_item.delay(item.pk)
    msg = 'Sincronização iniciada. As transações aparecerão em instantes.'
    if getattr(request, 'htmx', False):
        return HttpResponse(msg)
    messages.success(request, msg)
    return redirect('pluggy_list')


@login_required
@family_edit_required
@rate_limit_post('pluggy_disconnect')
@require_POST
def pluggy_disconnect(request, item_pk):
    group = request.user.profile.family_group
    item = get_object_or_404(PluggyItem, pk=item_pk, family_group=group, is_active=True)
    try:
        PluggyClient().delete_item(item.pluggy_item_id)
    except PluggyError as exc:
        logger.warning('Falha ao remover item no Pluggy %s: %s', item.pluggy_item_id, exc)
    item.is_active = False
    item.account_links.update(is_active=False)
    item.save(update_fields=['is_active', 'updated_at'])
    audit_security_event(
        request,
        SecurityEvent.PROFILE_CHANGED,
        metadata={'action': 'pluggy_disconnected', 'connector': item.connector_name},
    )
    messages.success(request, 'Conexão removida.')
    return redirect('pluggy_list')


@csrf_exempt
@require_POST
def pluggy_webhook(request):
    """Endpoint server-to-server do Pluggy. Valida segredo e dispara sync do item."""
    secret = settings.PLUGGY_WEBHOOK_SECRET
    if secret:
        provided = request.GET.get('token', '')
        if not constant_time_compare(provided, secret):
            return JsonResponse({'error': 'invalid token'}, status=403)

    try:
        payload = json.loads(request.body or '{}')
    except (ValueError, TypeError):
        return HttpResponseBadRequest('payload inválido')

    event = payload.get('event') or payload.get('type') or ''
    item_id = payload.get('itemId') or (payload.get('data') or {}).get('itemId')
    if item_id and event.startswith(('item', 'transactions')):
        item = PluggyItem.objects.filter(pluggy_item_id=item_id, is_active=True).first()
        if item:
            sync_pluggy_item.delay(item.pk)

    return JsonResponse({'received': True})
