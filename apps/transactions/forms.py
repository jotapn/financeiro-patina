from datetime import date

from django import forms
from django.db.models import Q

from apps.accounts.models import FinancialAccount, PaymentMethod
from apps.cards.models import CreditCard
from apps.categories.models import Category

from .models import Transaction


class TransactionForm(forms.ModelForm):
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

