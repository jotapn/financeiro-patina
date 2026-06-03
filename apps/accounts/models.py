from decimal import Decimal

from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce


MONEY_FIELD = DecimalField(max_digits=15, decimal_places=2)


class FinancialAccountQuerySet(models.QuerySet):
    def with_current_balance(self):
        from apps.transactions.models import Transaction

        zero = Value(Decimal('0'), output_field=MONEY_FIELD)

        def account_sum(**filters):
            return Coalesce(
                Subquery(
                    Transaction.objects.filter(account=OuterRef('pk'), status='paid', **filters)
                    .order_by()
                    .values('account')
                    .annotate(total=Sum('amount'))
                    .values('total')[:1],
                    output_field=MONEY_FIELD,
                ),
                zero,
                output_field=MONEY_FIELD,
            )

        transfer_in = Coalesce(
            Subquery(
                Transaction.objects.filter(
                    destination_account=OuterRef('pk'),
                    transaction_type='transfer',
                    status='paid',
                )
                .order_by()
                .values('destination_account')
                .annotate(total=Sum('amount'))
                .values('total')[:1],
                output_field=MONEY_FIELD,
            ),
            zero,
            output_field=MONEY_FIELD,
        )

        return self.annotate(
            _income_total=account_sum(transaction_type='income'),
            _expense_total=account_sum(transaction_type='expense'),
            _transfer_out_total=account_sum(transaction_type='transfer'),
            _transfer_in_total=transfer_in,
        ).annotate(
            _current_balance=ExpressionWrapper(
                F('initial_balance')
                + F('_income_total')
                - F('_expense_total')
                + F('_transfer_in_total')
                - F('_transfer_out_total'),
                output_field=MONEY_FIELD,
            )
        )


class FinancialAccount(models.Model):
    TYPE_CHOICES = [
        ('checking', 'Conta Corrente'),
        ('savings', 'Poupança'),
        ('wallet', 'Carteira/Espécie'),
        ('digital', 'Conta Digital'),
        ('investment', 'Conta Investimento'),
        ('salary', 'Conta Salário'),
    ]
    BANK_CHOICES = [
        ('nubank', 'Nubank'),
        ('itau', 'Itaú'),
        ('bradesco', 'Bradesco'),
        ('bb', 'Banco do Brasil'),
        ('caixa', 'Caixa'),
        ('inter', 'Inter'),
        ('xp', 'XP Investimentos'),
        ('btg', 'BTG Pactual'),
        ('c6', 'C6 Bank'),
        ('picpay', 'PicPay'),
        ('other', 'Outro'),
    ]
    OWNERSHIP_CHOICES = [('personal', 'Pessoal'), ('shared', 'Compartilhada')]

    owner = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='owned_accounts')
    family_group = models.ForeignKey(
        'core.FamilyGroup', on_delete=models.CASCADE, related_name='accounts'
    )
    ownership = models.CharField(max_length=10, choices=OWNERSHIP_CHOICES, default='personal')
    name = models.CharField(max_length=100, verbose_name='Nome da conta')
    account_type = models.CharField(max_length=15, choices=TYPE_CHOICES, verbose_name='Tipo')
    bank = models.CharField(max_length=15, choices=BANK_CHOICES, default='other')
    bank_custom = models.CharField(max_length=100, blank=True)
    initial_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name='Saldo inicial'
    )
    color = models.CharField(max_length=7, default='#7c3aed')
    icon = models.CharField(max_length=50, default='wallet')
    is_active = models.BooleanField(default=True)
    include_in_total = models.BooleanField(default=True, verbose_name='Incluir no total')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FinancialAccountQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Conta Financeira'
        verbose_name_plural = 'Contas Financeiras'

    def __str__(self):
        return f'{self.name} ({self.owner.get_full_name()})'

    @property
    def bank_display(self):
        if self.bank == 'other':
            return self.bank_custom or 'Outro'
        return dict(self.BANK_CHOICES).get(self.bank, self.bank)

    @property
    def current_balance(self):
        if hasattr(self, '_current_balance'):
            return self._current_balance

        from apps.transactions.models import Transaction

        income = (
            Transaction.objects.filter(account=self, transaction_type='income', status='paid').aggregate(
                t=Sum('amount')
            )['t']
            or Decimal('0')
        )
        expense = (
            Transaction.objects.filter(account=self, transaction_type='expense', status='paid').aggregate(
                t=Sum('amount')
            )['t']
            or Decimal('0')
        )
        transfer_in = (
            Transaction.objects.filter(
                destination_account=self, transaction_type='transfer', status='paid'
            ).aggregate(t=Sum('amount'))['t']
            or Decimal('0')
        )
        transfer_out = (
            Transaction.objects.filter(account=self, transaction_type='transfer', status='paid').aggregate(
                t=Sum('amount')
            )['t']
            or Decimal('0')
        )
        return self.initial_balance + income - expense + transfer_in - transfer_out


class PaymentMethod(models.Model):
    TYPE_CHOICES = [
        ('pix', 'PIX'),
        ('ted', 'TED/DOC'),
        ('boleto', 'Boleto'),
        ('debit', 'Débito'),
        ('cash', 'Dinheiro'),
        ('credit', 'Cartão de Crédito'),
        ('other', 'Outro'),
    ]

    family_group = models.ForeignKey(
        'core.FamilyGroup', on_delete=models.CASCADE, related_name='payment_methods'
    )
    name = models.CharField(max_length=50)
    method_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Método de Pagamento'

    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentMethod.objects.filter(family_group=self.family_group, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

