from calendar import monthrange
from datetime import date

from celery import shared_task
from dateutil.relativedelta import relativedelta

from .models import CardInvoice, CreditCard


def _safe_replace_day(any_date, day):
    return any_date.replace(day=min(day, monthrange(any_date.year, any_date.month)[1]))


@shared_task
def generate_monthly_invoices():
    current_month = date.today().replace(day=1)
    created = 0
    for card in CreditCard.objects.filter(is_active=True):
        ref = current_month + relativedelta(months=1)
        _, is_new = CardInvoice.objects.get_or_create(
            card=card,
            reference_month=ref,
            defaults={
                'closing_date': _safe_replace_day(ref, card.closing_day),
                'due_date': _safe_replace_day(ref + relativedelta(months=1), card.due_day),
                'status': 'future',
            },
        )
        created += int(is_new)
    return f'Faturas criadas: {created}'
