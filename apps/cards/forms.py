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
        labels = {
            'name': 'Nome do cartao',
            'brand': 'Bandeira',
            'last_four_digits': 'Ultimos 4 digitos',
            'holder_name': 'Nome impresso',
            'credit_limit': 'Limite de credito',
            'closing_day': 'Dia do fechamento',
            'due_day': 'Dia do vencimento',
            'debit_account': 'Conta de pagamento',
            'color_from': 'Cor inicial',
            'color_to': 'Cor final',
            'cashback_percentage': 'Cashback (%)',
            'annual_fee': 'Anuidade',
            'ownership': 'Titularidade',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input-glass', 'placeholder': 'Ex.: Nubank Ultravioleta'}),
            'brand': forms.Select(attrs={'class': 'input-glass'}),
            'last_four_digits': forms.TextInput(
                attrs={'class': 'input-glass', 'placeholder': '0000', 'maxlength': '4', 'inputmode': 'numeric'}
            ),
            'holder_name': forms.TextInput(attrs={'class': 'input-glass', 'placeholder': 'Nome como aparece no cartao'}),
            'credit_limit': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'closing_day': forms.NumberInput(
                attrs={'class': 'input-glass', 'placeholder': 'Ex.: 20', 'min': '1', 'max': '31'}
            ),
            'due_day': forms.NumberInput(
                attrs={'class': 'input-glass', 'placeholder': 'Ex.: 28', 'min': '1', 'max': '31'}
            ),
            'debit_account': forms.Select(attrs={'class': 'input-glass'}),
            'color_from': forms.TextInput(attrs={'type': 'color'}),
            'color_to': forms.TextInput(attrs={'type': 'color'}),
            'cashback_percentage': forms.NumberInput(
                attrs={'class': 'input-glass', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'annual_fee': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'ownership': forms.Select(attrs={'class': 'input-glass'}),
        }

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            self.fields['debit_account'].queryset = FinancialAccount.objects.filter(
                family_group=family_group, is_active=True
            ).order_by('name')
        self.fields['debit_account'].required = False
        self.fields['debit_account'].empty_label = 'Selecione a conta'


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
