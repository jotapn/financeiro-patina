from django.db import models


class Tag(models.Model):
    family_group = models.ForeignKey('core.FamilyGroup', on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#7c3aed')

    def __str__(self):
        return self.name


class RecurrenceRule(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Diária'),
        ('weekly', 'Semanal'),
        ('biweekly', 'Quinzenal'),
        ('monthly', 'Mensal'),
        ('quarterly', 'Trimestral'),
        ('yearly', 'Anual'),
    ]
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    interval = models.IntegerField(default=1)
    end_date = models.DateField(null=True, blank=True)
    max_occurrences = models.IntegerField(null=True, blank=True)
    occurrences_created = models.IntegerField(default=0)


class Transaction(models.Model):
    TYPE_CHOICES = [('income', 'Receita'), ('expense', 'Despesa'), ('transfer', 'Transferência')]
    STATUS_CHOICES = [('paid', 'Pago/Recebido'), ('pending', 'Pendente'), ('scheduled', 'Agendado')]

    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='transactions')
    family_group = models.ForeignKey(
        'core.FamilyGroup', on_delete=models.CASCADE, related_name='transactions'
    )
    account = models.ForeignKey(
        'accounts.FinancialAccount',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
    )
    destination_account = models.ForeignKey(
        'accounts.FinancialAccount',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transfers_received',
    )
    credit_card = models.ForeignKey(
        'cards.CreditCard',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
    )
    invoice = models.ForeignKey(
        'cards.CardInvoice',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
    )
    category = models.ForeignKey('categories.Category', on_delete=models.PROTECT, related_name='transactions')
    subcategory = models.ForeignKey(
        'categories.Subcategory',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transactions',
    )
    payment_method = models.ForeignKey('accounts.PaymentMethod', null=True, blank=True, on_delete=models.SET_NULL)
    tags = models.ManyToManyField('transactions.Tag', blank=True)

    parent_transaction = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='installments'
    )
    installment_number = models.IntegerField(null=True, blank=True)
    installment_total = models.IntegerField(null=True, blank=True)

    recurrence_rule = models.ForeignKey(RecurrenceRule, null=True, blank=True, on_delete=models.SET_NULL)

    description = models.CharField(max_length=255, verbose_name='Descrição')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name='Tipo')
    date = models.DateField(verbose_name='Data')
    due_date = models.DateField(null=True, blank=True, verbose_name='Vencimento')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='paid')
    notes = models.TextField(blank=True, verbose_name='Observações')
    receipt_image = models.ImageField(upload_to='receipts/%Y/%m/', null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, verbose_name='Estabelecimento')
    is_ignored = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        indexes = [
            models.Index(fields=['family_group', 'date']),
            models.Index(fields=['user', 'transaction_type']),
        ]

    def __str__(self):
        return f'{self.description} - R$ {self.amount}'

