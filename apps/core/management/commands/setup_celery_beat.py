from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Configura schedules padrão do Celery Beat para o FinanceFlow'

    def handle(self, *args, **options):
        schedules = {
            'update-stocks-15min': ('*/15', '9-18', '1-5', '*', '*', 'apps.investments.tasks.update_stock_prices'),
            'update-crypto-5min': ('*/5', '*', '*', '*', '*', 'apps.investments.tasks.update_crypto_prices'),
            'update-fixed-income-daily': ('0', '20', '*', '*', '*', 'apps.investments.tasks.update_fixed_income_returns'),
            'check-notifications-daily': ('0', '8', '*', '*', '*', 'apps.notifications.tasks.check_all_alerts'),
            'create-recurring-transactions': ('0', '7', '*', '*', '*', 'apps.transactions.tasks.create_scheduled_transactions'),
            'generate-monthly-invoices': ('30', '0', '*', '1', '*', 'apps.cards.tasks.generate_monthly_invoices'),
        }
        for name, (minute, hour, day_of_week, day_of_month, month_of_year, task_name) in schedules.items():
            crontab, _ = CrontabSchedule.objects.get_or_create(minute=minute, hour=hour, day_of_week=day_of_week, day_of_month=day_of_month, month_of_year=month_of_year)
            PeriodicTask.objects.update_or_create(name=name, defaults={'crontab': crontab, 'task': task_name})
        self.stdout.write(self.style.SUCCESS('Celery Beat configurado com sucesso.'))
