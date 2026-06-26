import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, queue='market_data')
def sync_pluggy_item(self, item_id):
    """Sincroniza um único item Pluggy (accounts + transações + saldo)."""
    from .client import PluggyError
    from .models import PluggyItem
    from .services import sync_item

    try:
        item = PluggyItem.objects.get(pk=item_id, is_active=True)
    except PluggyItem.DoesNotExist:
        return f'Item {item_id} inativo ou inexistente'

    try:
        summary = sync_item(item)
        return f'Item {item_id}: {summary["imported"]} transações, {summary["links"]} contas'
    except PluggyError as exc:
        item.status = PluggyItem.STATUS_ERROR
        item.error_message = str(exc)[:500]
        item.save(update_fields=['status', 'error_message'])
        logger.error('Falha ao sincronizar item Pluggy %s: %s', item_id, exc)
        raise self.retry(exc=exc, countdown=120)


@shared_task
def sync_all_pluggy_items():
    """Despacha a sincronização de todos os itens ativos (uso periódico)."""
    from .models import PluggyItem

    item_ids = list(PluggyItem.objects.filter(is_active=True).values_list('pk', flat=True))
    for item_id in item_ids:
        sync_pluggy_item.delay(item_id)
    return f'Disparados {len(item_ids)} itens'


@shared_task
def setup_pluggy_schedules():
    """Registra a tarefa periódica de sincronização (a cada 6h)."""
    from django_celery_beat.models import CrontabSchedule, PeriodicTask

    sched_6h, _ = CrontabSchedule.objects.get_or_create(
        minute='0', hour='*/6', day_of_week='*', day_of_month='*', month_of_year='*'
    )
    PeriodicTask.objects.get_or_create(
        name='Sincronizar contas Open Finance (Pluggy)',
        defaults={'crontab': sched_6h, 'task': 'apps.integrations.tasks.sync_all_pluggy_items'},
    )
    return 'Agenda Pluggy configurada'
