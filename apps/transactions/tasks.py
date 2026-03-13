from datetime import timedelta

from celery import shared_task
from dateutil.relativedelta import relativedelta

from apps.notifications.models import Notification

from .models import Transaction


def _get_next_date(base_date, frequency, interval):
    if frequency == 'daily':
        return base_date + timedelta(days=interval)
    if frequency == 'weekly':
        return base_date + timedelta(weeks=interval)
    if frequency == 'biweekly':
        return base_date + timedelta(days=14 * interval)
    if frequency == 'monthly':
        return base_date + relativedelta(months=interval)
    if frequency == 'quarterly':
        return base_date + relativedelta(months=3 * interval)
    if frequency == 'yearly':
        return base_date + relativedelta(years=interval)
    return base_date + timedelta(days=interval)


@shared_task
def create_scheduled_transactions():
    created = 0
    roots = Transaction.objects.filter(recurrence_rule__isnull=False, parent_transaction__isnull=True)
    for root in roots.select_related('recurrence_rule', 'user'):
        rule = root.recurrence_rule
        if rule.max_occurrences and rule.occurrences_created >= rule.max_occurrences:
            continue
        latest = root.installments.order_by('-date').first() or root
        next_date = _get_next_date(latest.date, rule.frequency, rule.interval)
        if rule.end_date and next_date > rule.end_date:
            continue
        if Transaction.objects.filter(parent_transaction=root, date=next_date).exists():
            continue
        scheduled = Transaction.objects.create(
            user=root.user,
            family_group=root.family_group,
            account=root.account,
            destination_account=root.destination_account,
            credit_card=root.credit_card,
            invoice=root.invoice,
            category=root.category,
            subcategory=root.subcategory,
            payment_method=root.payment_method,
            recurrence_rule=rule,
            description=root.description,
            amount=root.amount,
            transaction_type=root.transaction_type,
            date=next_date,
            due_date=next_date,
            status='scheduled',
            notes=root.notes,
            location=root.location,
            parent_transaction=root,
        )
        scheduled.tags.set(root.tags.all())
        rule.occurrences_created += 1
        rule.save(update_fields=['occurrences_created'])
        Notification.objects.create(
            user=root.user,
            notification_type='recurring',
            title='Transação recorrente criada',
            message=f'{root.description} foi agendada para {next_date.strftime("%d/%m/%Y")}.',
            action_url=f'/transactions/{scheduled.pk}/confirm/',
        )
        created += 1
    return f'Transações agendadas criadas: {created}'
