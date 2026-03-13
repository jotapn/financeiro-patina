from datetime import date, timedelta

from celery import shared_task

from apps.budgets.models import Budget, FinancialGoal
from apps.cards.models import CardInvoice
from apps.notifications.models import Notification


@shared_task
def check_all_alerts():
    today = date.today()
    created = 0

    for budget in Budget.objects.filter(reference_month__year=today.year, reference_month__month=today.month):
        if budget.owner and budget.percentage_used >= budget.alert_threshold:
            _, is_new = Notification.objects.get_or_create(
                user=budget.owner,
                notification_type='budget',
                title=f'Orçamento em alerta: {budget.category.name if budget.category else "Sem categoria"}',
                message=f'Você já usou {budget.percentage_used}% do orçamento do mês.',
                action_url='/budgets/',
            )
            created += int(is_new)

    invoices = CardInvoice.objects.filter(status__in=('open', 'partial', 'overdue'), due_date__lte=today + timedelta(days=7)).select_related('card__owner', 'card')
    for invoice in invoices:
        _, is_new = Notification.objects.get_or_create(
            user=invoice.card.owner,
            notification_type='bill',
            title=f'Fatura próxima do vencimento: {invoice.card.name}',
            message=f'Vencimento em {invoice.due_date.strftime("%d/%m/%Y")} no valor de R$ {invoice.total_amount}.',
            action_url=f'/cards/{invoice.card_id}/?invoice={invoice.pk}',
        )
        created += int(is_new)

    for goal in FinancialGoal.objects.filter(is_completed=False):
        if goal.target_date <= today + timedelta(days=30):
            _, is_new = Notification.objects.get_or_create(
                user=goal.owner,
                notification_type='goal',
                title=f'Meta perto do prazo: {goal.name}',
                message=f'Sua meta vence em {goal.target_date.strftime("%d/%m/%Y")} e está em {goal.percentage_complete}%.',
                action_url='/budgets/',
            )
            created += int(is_new)

    return f'Notificações criadas: {created}'
