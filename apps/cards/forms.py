from datetime import date

from django import forms

from apps.accounts.models import FinancialAccount

from .models import CreditCard


class CreditCardForm(forms.ModelForm):
    class Meta:
        model = CreditCard
        fields = [
            'name',
            'brand',
            'last_four_digits',
            'holder_name',
            'credit_limit',
            'closing_day',
            'due_day',
            'debit_account',
            'color_from',
            'color_to',
            'cashback_percentage',
            'annual_fee',
            'ownership',
        ]
        widgets = {
            'color_from': forms.TextInput(attrs={'type': 'color'}),
            'color_to': forms.TextInput(attrs={'type': 'color'}),
        }

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            self.fields['debit_account'].queryset = FinancialAccount.objects.filter(
                family_group=family_group, is_active=True
            )
        self.fields['debit_account'].required = False


class InvoicePaymentForm(forms.Form):
    amount = forms.DecimalField(max_digits=15, decimal_places=2, label='Valor pago')
    account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), label='Conta de débito')
    payment_date = forms.DateField(
        initial=date.today,
        label='Data do pagamento',
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )

    def __init__(self, *args, invoice=None, **kwargs):
        super().__init__(*args, **kwargs)
        if invoice:
            self.fields['amount'].initial = invoice.total_amount
            group = invoice.card.family_group
            self.fields['account'].queryset = FinancialAccount.objects.filter(
                family_group=group, is_active=True
            )
            if invoice.card.debit_account:
                self.fields['account'].initial = invoice.card.debit_account
