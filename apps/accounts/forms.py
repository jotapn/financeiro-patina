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
        labels = {
            'name': 'Nome da conta',
            'account_type': 'Tipo de conta',
            'bank': 'Banco',
            'bank_custom': 'Nome do banco',
            'initial_balance': 'Saldo inicial',
            'color': 'Cor de destaque',
            'ownership': 'Titularidade',
            'include_in_total': 'Incluir no saldo total',
            'is_active': 'Conta ativa',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Digite o nome da conta', 'class': 'input-glass'}),
            'bank_custom': forms.TextInput(attrs={'placeholder': 'Digite o nome do banco', 'class': 'input-glass'}),
            'initial_balance': forms.NumberInput(
                attrs={
                    'step': '0.01',
                    'placeholder': '0.00',
                    'inputmode': 'decimal',
                    'class': 'input-glass input-with-prefix',
                }
            ),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_custom'].required = False
        self.fields['bank_custom'].help_text = 'Preencha apenas se selecionar "Outro".'
        self.fields['include_in_total'].widget.attrs.update({'class': 'toggle-input'})
        self.fields['is_active'].widget.attrs.update({'class': 'toggle-input'})
        self.fields['bank'].widget.attrs.update({'x-model': 'bank'})

        self.fields['account_type'].choices = [('', 'Selecione o tipo')] + [
            choice for choice in self.fields['account_type'].choices if choice[0]
        ]
        self.fields['bank'].choices = [choice for choice in self.fields['bank'].choices if choice[0]]
        self.fields['ownership'].choices = [choice for choice in self.fields['ownership'].choices if choice[0]]


class TransferForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), label='Conta de origem')
    to_account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), label='Conta de destino')
    amount = forms.DecimalField(max_digits=15, decimal_places=2, label='Valor')
    date = forms.DateField(
        initial=date.today,
        label='Data da transferência',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'input-glass'}),
    )
    description = forms.CharField(
        max_length=255,
        required=False,
        label='Descrição',
        widget=forms.TextInput(attrs={'placeholder': 'Ex.: Reserva mensal', 'class': 'input-glass'}),
    )

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            qs = FinancialAccount.objects.filter(family_group=family_group, is_active=True)
            self.fields['from_account'].queryset = qs
            self.fields['to_account'].queryset = qs

        self.fields['from_account'].empty_label = 'Selecione a origem'
        self.fields['to_account'].empty_label = 'Selecione o destino'
