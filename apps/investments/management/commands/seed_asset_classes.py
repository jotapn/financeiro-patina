from django.core.management.base import BaseCommand

from apps.investments.models import AssetClass

ASSET_CLASSES = [
    ('Ações', 'stocks', '#3b82f6', 'trending-up', 0, True, 15.0),
    ('FIIs', 'fii', '#10b981', 'building-2', 0, True, 20.0),
    ('CDB/LCI/LCA', 'fixed_postfixed', '#f59e0b', 'landmark', 0, True, 15.0),
    ('Tesouro Direto', 'treasury', '#8b5cf6', 'shield', 1, True, 15.0),
    ('Renda Fixa Pré', 'fixed_prefixed', '#f97316', 'percent', 0, True, 15.0),
    ('Criptomoedas', 'crypto', '#06b6d4', 'bitcoin', 0, False, 0.0),
    ('ETF', 'etf', '#ec4899', 'bar-chart', 0, True, 15.0),
    ('BDR', 'bdr', '#84cc16', 'globe', 0, True, 15.0),
    ('Previdência Privada', 'pension', '#64748b', 'umbrella', 365, True, 10.0),
    ('Poupança', 'savings', '#0ea5e9', 'piggy-bank', 0, False, 0.0),
    ('Outro', 'other', '#94a3b8', 'package', 0, False, 0.0),
]


class Command(BaseCommand):
    help = 'Popula classes de ativos padrão'

    def handle(self, *args, **options):
        created = 0
        for name, atype, color, icon, liq, taxable, ir_rate in ASSET_CLASSES:
            _, is_new = AssetClass.objects.get_or_create(
                asset_type=atype,
                defaults={
                    'name': name,
                    'color': color,
                    'icon': icon,
                    'liquidity_days': liq,
                    'is_taxable': taxable,
                    'ir_rate': ir_rate,
                    'is_system': True,
                },
            )
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Classes criadas: {created}'))
