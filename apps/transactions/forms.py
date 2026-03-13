from datetime import date

from django import forms
from django.db.models import Q

from apps.accounts.models import FinancialAccount, PaymentMethod
from apps.cards.models import CreditCard
from apps.categories.models import Category

from .models import RecurrenceRule, Transaction


class TransactionForm(forms.ModelForm):
    recurrence_frequency = forms.ChoiceField(
        choices=[('', 'Sem recorrência')] + RecurrenceRule.FREQUENCY_CHOICES,
        required=False,
        label='Recorrência',
    )
    recurrence_interval = forms.IntegerField(required=False, min_value=1, initial=1, label='Intervalo')
    recurrence_end_date = forms.DateField(
        required=False,
        label='Fim da recorrência',
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )
    recurrence_max_occurrences = forms.IntegerField(required=False, min_value=1, label='Máximo de ocorrências')

    class Meta:
        model = Transaction
        fields = [
            'description',
            'amount',
            'transaction_type',
            'date',
            'account',
            'credit_card',
            'category',
            'subcategory',
            'payment_method',
            'status',
            'due_date',
            'notes',
            'location',
            'receipt_image',
            'tags',
            'installment_number',
            'installment_total',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'due_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            self.fields['account'].queryset = FinancialAccount.objects.filter(
                family_group=family_group, is_active=True
            )
            self.fields['credit_card'].queryset = CreditCard.objects.filter(
                family_group=family_group, is_active=True
            )
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                family_group=family_group, is_active=True
            )
            self.fields['category'].queryset = Category.objects.filter(
                Q(family_group=family_group) | Q(is_system=True)
            ).order_by('name')
        self.fields['date'].initial = date.today
        required = {'description', 'amount', 'transaction_type', 'date', 'category'}
        for name, field in self.fields.items():
            field.required = name in required

        if self.instance and self.instance.recurrence_rule_id:
            rule = self.instance.recurrence_rule
            self.fields['recurrence_frequency'].initial = rule.frequency
            self.fields['recurrence_interval'].initial = rule.interval
            self.fields['recurrence_end_date'].initial = rule.end_date
            self.fields['recurrence_max_occurrences'].initial = rule.max_occurrences

