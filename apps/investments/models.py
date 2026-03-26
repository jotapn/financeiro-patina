from datetime import date
from decimal import Decimal

from django.db import models


class AssetClass(models.Model):
    TYPE_CHOICES = [
        ('stocks', 'Ações'),
        ('fii', 'FIIs'),
        ('fixed_prefixed', 'Renda Fixa Pré-Fixada'),
        ('fixed_postfixed', 'Renda Fixa Pós-Fixada'),
        ('treasury', 'Tesouro Direto'),
        ('crypto', 'Criptomoedas'),
        ('pension', 'Previdência Privada'),
        ('savings', 'Poupança'),
        ('etf', 'ETF'),
        ('bdr', 'BDR'),
        ('other', 'Outro'),
    ]

    name = models.CharField(max_length=50)
    asset_type = models.CharField(max_length=20, choices=TYPE_CHOICES, unique=True)
    color = models.CharField(max_length=7, default='#7c3aed')
    icon = models.CharField(max_length=50, default='trending-up')
    liquidity_days = models.IntegerField(default=0, help_text='D+0, D+1, etc.')
    is_taxable = models.BooleanField(default=True)
    ir_rate = models.DecimalField(max_digits=5, decimal_places=2, default=15)
    is_system = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Classe de Ativo'

    def __str__(self):
        return self.name


class Investment(models.Model):
    RATE_TYPE_CHOICES = [
        ('prefixed', 'Pré-fixado % a.a.'),
        ('cdi', '% do CDI'),
        ('ipca', 'IPCA + % a.a.'),
        ('selic', 'Selic'),
        ('other', 'Outro'),
    ]
    OWNERSHIP_CHOICES = [('personal', 'Pessoal'), ('shared', 'Compartilhado')]

    owner = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.CASCADE, related_name='investments'
    )
    family_group = models.ForeignKey('core.FamilyGroup', on_delete=models.CASCADE, related_name='investments')
    asset_class = models.ForeignKey(
        AssetClass, null=True, blank=True, on_delete=models.PROTECT, related_name='investments'
    )
    ownership = models.CharField(max_length=10, choices=OWNERSHIP_CHOICES, default='personal')

    name = models.CharField(max_length=200, verbose_name='Nome')
    ticker = models.CharField(max_length=20, blank=True, default='', verbose_name='Ticker')
    institution = models.CharField(max_length=100, blank=True, default='', verbose_name='Instituição')

    quantity = models.DecimalField(max_digits=24, decimal_places=8, default=0, verbose_name='Quantidade')
    average_price = models.DecimalField(max_digits=20, decimal_places=8, default=0, verbose_name='Preço médio')
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0, verbose_name='Preço atual')
    last_price_update = models.DateTimeField(null=True, blank=True)

    rate_type = models.CharField(max_length=10, choices=RATE_TYPE_CHOICES, null=True, blank=True)
    rate_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Taxa (%)')
    maturity_date = models.DateField(null=True, blank=True, verbose_name='Vencimento')
    invested_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor aplicado')

    current_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_invested = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_earnings = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_dividends = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    daily_change = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    daily_change_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-current_value']
        verbose_name = 'Investimento'
        verbose_name_plural = 'Investimentos'

    def __str__(self):
        return f'{self.name} ({self.ticker or (self.asset_class.name if self.asset_class else "Sem classe")})'

    @property
    def profit_loss(self):
        return self.current_value - self.total_invested

    @property
    def profit_loss_pct(self):
        if self.total_invested == 0:
            return Decimal('0')
        return (self.profit_loss / self.total_invested * 100).quantize(Decimal('0.01'))

    @property
    def is_fixed_income(self):
        if not self.asset_class:
            return False
        return self.asset_class.asset_type in ('fixed_prefixed', 'fixed_postfixed', 'treasury', 'savings', 'pension')

    @property
    def is_variable_income(self):
        if not self.asset_class:
            return False
        return self.asset_class.asset_type in ('stocks', 'fii', 'etf', 'bdr')

    @property
    def is_crypto(self):
        return bool(self.asset_class and self.asset_class.asset_type == 'crypto')

    def initialize_snapshot(self):
        if self.transactions.exists():
            self.recalculate()
            return

        if self.is_fixed_income:
            base_amount = self.invested_amount or Decimal('0')
            self.total_invested = base_amount
            self.current_value = base_amount + (self.total_earnings or Decimal('0'))
        else:
            quantity = self.quantity or Decimal('0')
            average_price = self.average_price or Decimal('0')
            current_price = self.current_price or average_price
            self.total_invested = quantity * average_price
            self.current_value = quantity * current_price

        self.save(update_fields=['total_invested', 'current_value'])

    def recalculate(self):
        from django.db.models import Sum

        buys = self.transactions.filter(transaction_type='buy')
        sells = self.transactions.filter(transaction_type='sell')

        total_qty_bought = buys.aggregate(t=Sum('quantity'))['t'] or Decimal('0')
        total_qty_sold = sells.aggregate(t=Sum('quantity'))['t'] or Decimal('0')
        self.quantity = total_qty_bought - total_qty_sold

        total_cost = sum((t.quantity or 0) * (t.price or 0) + (t.fees or 0) for t in buys)
        if total_qty_bought > 0:
            self.average_price = Decimal(str(total_cost)) / total_qty_bought

        self.total_invested = sum((t.quantity or 0) * (t.price or 0) + (t.fees or 0) for t in buys) - sum(
            (t.quantity or 0) * (t.price or 0) - (t.fees or 0) for t in sells
        )

        dividends_total = self.transactions.filter(transaction_type__in=('dividend', 'jcp', 'income')).aggregate(
            t=Sum('amount')
        )['t'] or Decimal('0')
        self.total_dividends = dividends_total

        if self.is_fixed_income:
            self.current_value = self.invested_amount + self.total_earnings
        else:
            self.current_value = self.quantity * self.current_price

        self.save()


class InvestmentTransaction(models.Model):
    TYPE_CHOICES = [
        ('buy', 'Compra'),
        ('sell', 'Venda'),
        ('dividend', 'Dividendo'),
        ('jcp', 'JCP'),
        ('income', 'Rendimento'),
        ('split', 'Desdobramento'),
        ('grouping', 'Grupamento'),
    ]

    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date = models.DateField(verbose_name='Data')
    quantity = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True, verbose_name='Quantidade')
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True, verbose_name='Preço unitário')
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor total')
    fees = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Taxas')
    ir_withheld = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='IR retido')
    broker = models.CharField(max_length=100, blank=True, verbose_name='Corretora')
    notes = models.TextField(blank=True)
    financial_transaction = models.ForeignKey(
        'transactions.Transaction', null=True, blank=True, on_delete=models.SET_NULL, related_name='investment_transactions'
    )

    class Meta:
        ordering = ['-date']
        verbose_name = 'Transação de Investimento'

    def __str__(self):
        return f'{self.get_transaction_type_display()} {self.investment.name} - {self.date}'

    def save(self, *args, **kwargs):
        if not self.amount and self.quantity and self.price:
            self.amount = self.quantity * self.price
        super().save(*args, **kwargs)
        self.investment.recalculate()


class InvestmentGoal(models.Model):
    family_group = models.ForeignKey('core.FamilyGroup', on_delete=models.CASCADE, related_name='investment_goals')
    owner = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='investment_goals')
    name = models.CharField(max_length=100)
    asset_class = models.ForeignKey(AssetClass, null=True, blank=True, on_delete=models.SET_NULL)
    investment = models.ForeignKey(
        Investment, null=True, blank=True, on_delete=models.SET_NULL, related_name='goals'
    )
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    target_date = models.DateField()
    monthly_contribution = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    color = models.CharField(max_length=7, default='#7c3aed')
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['target_date']
        verbose_name = 'Meta de Investimento'

    def __str__(self):
        return self.name

    @property
    def current_amount(self):
        if self.investment:
            return self.investment.current_value
        if self.asset_class:
            return sum(
                inv.current_value
                for inv in self.family_group.investments.filter(
                    asset_class=self.asset_class, owner=self.owner, is_active=True
                )
            )
        return Decimal('0')

    @property
    def percentage_complete(self):
        if self.target_amount == 0:
            return 0
        return min(round(float(self.current_amount / self.target_amount * 100), 1), 100)
