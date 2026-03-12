from datetime import date

from django import forms

from .models import FinancialAccount


class FinancialAccountForm(forms.ModelForm):
    class Meta:
        model = FinancialAccount
        fields = [
            'name',
            'account_type',
            'bank',
            'bank_custom',
            'initial_balance',
            'color',
            'ownership',
            'include_in_total',
            'is_active',
        ]
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }


class TransferForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), label='De')
    to_account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), label='Para')
    amount = forms.DecimalField(max_digits=15, decimal_places=2, label='Valor')
    date = forms.DateField(initial=date.today, label='Data')
    description = forms.CharField(max_length=255, required=False, label='Descrição')

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            qs = FinancialAccount.objects.filter(family_group=family_group, is_active=True)
            self.fields['from_account'].queryset = qs
            self.fields['to_account'].queryset = qs

