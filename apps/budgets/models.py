from datetime import date
from decimal import Decimal

from django.db import models
from django.db.models import Sum


class Budget(models.Model):
    PERIOD_CHOICES = [('monthly', 'Mensal'), ('yearly', 'Anual')]
    SCOPE_CHOICES = [('personal', 'Pessoal'), ('family', 'Familiar')]

    family_group = models.ForeignKey('core.FamilyGroup', on_delete=models.CASCADE, related_name='budgets')
    owner = models.ForeignKey(
        'core.User', null=True, blank=True, on_delete=models.CASCADE, related_name='budgets'
    )
    category = models.ForeignKey(
        'categories.Category', null=True, blank=True, on_delete=models.CASCADE, related_name='budgets'
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Limite')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='monthly')
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default='personal')
    reference_month = models.DateField(default=date.today, verbose_name='Mês de referência')
    rollover = models.BooleanField(default=False, verbose_name='Acumular saldo')
    alert_threshold = models.IntegerField(default=80, verbose_name='Alertar em %')
    # Legacy fields from Fase 1, kept to preserve backward-compatible migrations.
    name = models.CharField(max_length=100, blank=True, default='')
    month = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-reference_month', 'category__name']
        verbose_name = 'Orçamento'
        unique_together = ['owner', 'category', 'reference_month', 'scope']

    def __str__(self):
        if self.category:
            return f'{self.category.name} - {self.reference_month.strftime("%m/%Y")}'
        return self.name or f'Orçamento {self.pk}'

    @property
    def spent_amount(self):
        if hasattr(self, '_spent_amount'):
            return self._spent_amount

        if not self.category_id:
            return Decimal('0')
        from apps.transactions.models import Transaction

        qs = Transaction.objects.filter(
            family_group=self.family_group,
            category=self.category,
            transaction_type='expense',
            date__year=self.reference_month.year,
            date__month=self.reference_month.month,
            status='paid',
            is_ignored=False,
        )
        if self.scope == 'personal':
            qs = qs.filter(user=self.owner)
        return qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')

    @property
    def percentage_used(self):
        if self.amount == 0:
            return 0
        return min(round(float(self.spent_amount / self.amount * 100), 1), 100)

    @property
    def remaining(self):
        return max(self.amount - self.spent_amount, Decimal('0'))

    @property
    def is_over_budget(self):
        return self.spent_amount > self.amount

    @property
    def status_color(self):
        pct = self.percentage_used
        if pct >= 100:
            return '#ef4444'
        if pct >= 80:
            return '#f59e0b'
        return '#10b981'


class FinancialGoal(models.Model):
    TYPE_CHOICES = [
        ('savings', 'Reserva/Poupança'),
        ('debt_payoff', 'Quitar Dívida'),
        ('purchase', 'Compra Planejada'),
        ('emergency', 'Fundo de Emergência'),
        ('investment', 'Meta de Investimento'),
        ('travel', 'Viagem'),
    ]
    SCOPE_CHOICES = [('personal', 'Pessoal'), ('family', 'Familiar')]

    family_group = models.ForeignKey('core.FamilyGroup', on_delete=models.CASCADE, related_name='goals')
    owner = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=100, verbose_name='Nome da meta')
    goal_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default='personal')
    target_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor alvo')
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor atual')
    target_date = models.DateField(verbose_name='Data alvo')
    linked_account = models.ForeignKey(
        'accounts.FinancialAccount', null=True, blank=True, on_delete=models.SET_NULL, related_name='goals'
    )
    monthly_contribution = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    color = models.CharField(max_length=7, default='#7c3aed')
    icon = models.CharField(max_length=50, default='target')
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['target_date']
        verbose_name = 'Meta Financeira'

    def __str__(self):
        return self.name

    @property
    def percentage_complete(self):
        if self.target_amount == 0:
            return 0
        return min(round(float(self.current_amount / self.target_amount * 100), 1), 100)

    @property
    def months_remaining(self):
        today = date.today()
        return max((self.target_date.year - today.year) * 12 + (self.target_date.month - today.month), 1)

    @property
    def suggested_monthly(self):
        remaining = self.target_amount - self.current_amount
        return max(remaining / self.months_remaining, Decimal('0'))

    @property
    def on_track(self):
        return self.monthly_contribution >= self.suggested_monthly


class GoalContribution(models.Model):
    goal = models.ForeignKey(FinancialGoal, on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField(default=date.today)
    notes = models.CharField(max_length=200, blank=True)
    transaction = models.OneToOneField('transactions.Transaction', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-date']
