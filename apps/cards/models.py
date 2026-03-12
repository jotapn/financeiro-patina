from datetime import date
from decimal import Decimal

from django.db import models


class CreditCard(models.Model):
    BRAND_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('elo', 'Elo'),
        ('amex', 'American Express'),
        ('hipercard', 'Hipercard'),
        ('other', 'Outro'),
    ]
    OWNERSHIP_CHOICES = [('personal', 'Pessoal'), ('shared', 'Compartilhado')]

    owner = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='credit_cards')
    family_group = models.ForeignKey('core.FamilyGroup', on_delete=models.CASCADE, related_name='credit_cards')
    ownership = models.CharField(max_length=10, choices=OWNERSHIP_CHOICES, default='personal')
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=15, choices=BRAND_CHOICES)
    last_four_digits = models.CharField(max_length=4)
    holder_name = models.CharField(max_length=100)
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2)
    closing_day = models.IntegerField()
    due_day = models.IntegerField()
    debit_account = models.ForeignKey(
        'accounts.FinancialAccount', on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_cards'
    )
    color_from = models.CharField(max_length=7, default='#7c3aed')
    color_to = models.CharField(max_length=7, default='#3b82f6')
    cashback_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    annual_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Cartão de Crédito'

    def __str__(self):
        return f'{self.name} ****{self.last_four_digits}'

    @property
    def current_invoice(self):
        return self.invoices.filter(status='open').order_by('reference_month').first()

    @property
    def available_limit(self):
        inv = self.current_invoice
        if inv:
            return self.credit_limit - inv.total_amount
        return self.credit_limit

    @property
    def utilization_percentage(self):
        if self.credit_limit == 0:
            return 0
        return round(float((1 - self.available_limit / self.credit_limit) * 100), 1)


class CardInvoice(models.Model):
    STATUS_CHOICES = [
        ('future', 'Futura'),
        ('open', 'Aberta'),
        ('closed', 'Fechada'),
        ('paid', 'Paga'),
        ('partial', 'Pago Parcial'),
        ('overdue', 'Vencida'),
    ]

    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name='invoices')
    reference_month = models.DateField()
    closing_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    payment_date = models.DateField(null=True, blank=True)
    payment_transaction = models.ForeignKey(
        'transactions.Transaction', null=True, blank=True, on_delete=models.SET_NULL, related_name='paid_invoices'
    )

    class Meta:
        ordering = ['-reference_month']
        unique_together = ['card', 'reference_month']
        verbose_name = 'Fatura'

    def __str__(self):
        return f'Fatura {self.reference_month.strftime("%m/%Y")} - {self.card.name}'

    @property
    def days_until_due(self):
        return (self.due_date - date.today()).days

    @property
    def minimum_payment(self):
        return max(self.total_amount * Decimal('0.15'), Decimal('50'))
