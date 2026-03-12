import logging
from decimal import Decimal

import httpx
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def update_stock_prices(self):
    from django.utils import timezone

    from .models import Investment

    investments = Investment.objects.filter(
        is_active=True,
        asset_class__asset_type__in=('stocks', 'fii', 'etf', 'bdr'),
    ).exclude(ticker='')

    tickers = list(set(investments.values_list('ticker', flat=True)))
    if not tickers:
        return 'Nenhum ticker para atualizar'

    updated = 0
    for i in range(0, len(tickers), 10):
        batch = tickers[i : i + 10]
        tickers_str = ','.join(batch)
        try:
            resp = httpx.get(
                f'https://brapi.dev/api/quote/{tickers_str}',
                timeout=15,
                params={'token': 'demo'},
            )
            resp.raise_for_status()
            data = resp.json()

            for quote in data.get('results', []):
                ticker = quote.get('symbol', '')
                price = quote.get('regularMarketPrice')
                change = quote.get('regularMarketChange', 0)
                change_pct = quote.get('regularMarketChangePercent', 0)

                if price:
                    Investment.objects.filter(ticker=ticker, is_active=True).update(
                        current_price=Decimal(str(price)),
                        daily_change=Decimal(str(change or 0)),
                        daily_change_pct=Decimal(str(change_pct or 0)),
                        last_price_update=timezone.now(),
                    )
                    for inv in Investment.objects.filter(ticker=ticker, is_active=True):
                        inv.current_value = inv.quantity * Decimal(str(price))
                        inv.save(update_fields=['current_value'])
                    updated += 1

        except Exception as exc:
            logger.error(f'Erro ao atualizar {batch}: {exc}')
            raise self.retry(exc=exc, countdown=60)

    return f'Atualizado: {updated} ativos'


@shared_task(bind=True, max_retries=3)
def update_crypto_prices(self):
    from django.utils import timezone

    from .models import Investment

    investments = Investment.objects.filter(is_active=True, asset_class__asset_type='crypto').exclude(ticker='')

    if not investments.exists():
        return 'Nenhuma cripto para atualizar'

    coingecko_ids = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'ADA': 'cardano',
        'DOT': 'polkadot',
        'MATIC': 'matic-network',
        'LINK': 'chainlink',
        'AVAX': 'avalanche-2',
        'XRP': 'ripple',
        'DOGE': 'dogecoin',
        'LTC': 'litecoin',
    }

    tickers = list(set(investments.values_list('ticker', flat=True)))
    coin_ids = [coingecko_ids.get(t.upper(), t.lower()) for t in tickers]

    try:
        resp = httpx.get(
            'https://api.coingecko.com/api/v3/simple/price',
            params={
                'ids': ','.join(coin_ids),
                'vs_currencies': 'brl',
                'include_24hr_change': 'true',
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        updated = 0
        for ticker in tickers:
            coin_id = coingecko_ids.get(ticker.upper(), ticker.lower())
            coin_data = data.get(coin_id, {})
            price_brl = coin_data.get('brl')
            change_24h = coin_data.get('brl_24h_change', 0)

            if price_brl:
                Investment.objects.filter(ticker__iexact=ticker, is_active=True).update(
                    current_price=Decimal(str(price_brl)),
                    daily_change_pct=Decimal(str(change_24h or 0)),
                    last_price_update=timezone.now(),
                )
                for inv in Investment.objects.filter(ticker__iexact=ticker, is_active=True):
                    inv.current_value = inv.quantity * Decimal(str(price_brl))
                    inv.save(update_fields=['current_value'])
                updated += 1

        return f'Cripto atualizada: {updated}'

    except Exception as exc:
        logger.error(f'Erro CoinGecko: {exc}')
        raise self.retry(exc=exc, countdown=120)


@shared_task
def update_fixed_income_returns():
    from datetime import date

    from .models import Investment, InvestmentTransaction

    try:
        resp = httpx.get(
            'https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados/ultimos/1',
            params={'formato': 'json'},
            timeout=10,
        )
        resp.raise_for_status()
        cdi_daily_rate = Decimal(str(resp.json()[0]['valor'])) / 100
    except Exception as exc:
        logger.error(f'Erro ao buscar CDI: {exc}')
        cdi_daily_rate = Decimal('0.000465')

    fixed_investments = Investment.objects.filter(
        is_active=True,
        asset_class__asset_type__in=('fixed_postfixed', 'fixed_prefixed', 'treasury', 'savings'),
    )

    for inv in fixed_investments:
        if not inv.rate_type or not inv.rate_value:
            continue

        if inv.rate_type == 'cdi':
            daily_yield = inv.invested_amount * (cdi_daily_rate * inv.rate_value / 100)
        elif inv.rate_type == 'prefixed':
            annual_rate = inv.rate_value / 100
            daily_yield = inv.invested_amount * (Decimal(str((1 + float(annual_rate)) ** (1 / 252) - 1)))
        else:
            continue

        InvestmentTransaction.objects.create(
            investment=inv,
            transaction_type='income',
            date=date.today(),
            amount=daily_yield.quantize(Decimal('0.01')),
            notes='Rendimento automático calculado',
        )
        inv.total_earnings += daily_yield
        inv.current_value = inv.invested_amount + inv.total_earnings
        inv.save(update_fields=['total_earnings', 'current_value'])

    return f'Renda fixa atualizada: {fixed_investments.count()} ativos'


@shared_task
def setup_investment_schedules():
    from django_celery_beat.models import CrontabSchedule, PeriodicTask

    sched_15min, _ = CrontabSchedule.objects.get_or_create(
        minute='*/15', hour='9-18', day_of_week='1-5', day_of_month='*', month_of_year='*'
    )
    PeriodicTask.objects.get_or_create(
        name='Atualizar cotações B3',
        defaults={'crontab': sched_15min, 'task': 'apps.investments.tasks.update_stock_prices'},
    )

    sched_5min, _ = CrontabSchedule.objects.get_or_create(
        minute='*/5', hour='*', day_of_week='*', day_of_month='*', month_of_year='*'
    )
    PeriodicTask.objects.get_or_create(
        name='Atualizar cotações cripto',
        defaults={'crontab': sched_5min, 'task': 'apps.investments.tasks.update_crypto_prices'},
    )

    sched_daily, _ = CrontabSchedule.objects.get_or_create(
        minute='30', hour='18', day_of_week='1-5', day_of_month='*', month_of_year='*'
    )
    PeriodicTask.objects.get_or_create(
        name='Calcular rendimentos renda fixa',
        defaults={'crontab': sched_daily, 'task': 'apps.investments.tasks.update_fixed_income_returns'},
    )
