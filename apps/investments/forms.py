from datetime import date

from django import forms

from .models import AssetClass, Investment, InvestmentGoal, InvestmentTransaction


class AssetClassSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        option_value = getattr(value, 'value', value)
        if option_value and hasattr(self.choices, 'queryset'):
            try:
                asset_class = self.choices.queryset.get(pk=option_value)
                option['attrs']['data-asset-type'] = asset_class.asset_type
            except AssetClass.DoesNotExist:
                pass
        return option


class InvestmentForm(forms.ModelForm):
    class Meta:
        model = Investment
        fields = [
            'name',
            'asset_class',
            'ticker',
            'institution',
            'ownership',
            'quantity',
            'average_price',
            'current_price',
            'rate_type',
            'rate_value',
            'maturity_date',
            'invested_amount',
            'notes',
        ]
        labels = {
            'name': 'Nome do ativo',
            'asset_class': 'Classe do ativo',
            'ticker': 'Ticker ou codigo',
            'institution': 'Instituicao',
            'ownership': 'Titularidade',
            'quantity': 'Quantidade',
            'average_price': 'Preco medio',
            'current_price': 'Preco atual',
            'rate_type': 'Tipo de taxa',
            'rate_value': 'Taxa (%)',
            'maturity_date': 'Data de vencimento',
            'invested_amount': 'Valor aplicado',
            'notes': 'Observacoes',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input-glass', 'placeholder': 'Ex.: Tesouro Selic 2029'}),
            'asset_class': AssetClassSelect(attrs={'class': 'input-glass', 'x-ref': 'assetClassSelect', '@change': 'updateAssetType()'}),
            'ticker': forms.TextInput(attrs={'class': 'input-glass', 'placeholder': 'Ex.: PETR4, BTC, CDB'}),
            'institution': forms.TextInput(attrs={'class': 'input-glass', 'placeholder': 'Ex.: XP, Inter, Nubank'}),
            'ownership': forms.Select(attrs={'class': 'input-glass'}),
            'quantity': forms.NumberInput(attrs={'class': 'input-glass', 'placeholder': '0.00000000', 'step': '0.00000001'}),
            'average_price': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.00000001'}
            ),
            'current_price': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.00000001'}
            ),
            'rate_type': forms.Select(attrs={'class': 'input-glass'}),
            'rate_value': forms.NumberInput(attrs={'class': 'input-glass', 'placeholder': '0.00', 'step': '0.01'}),
            'maturity_date': forms.DateInput(attrs={'type': 'date', 'class': 'input-glass'}, format='%Y-%m-%d'),
            'invested_amount': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'notes': forms.Textarea(
                attrs={'rows': 3, 'class': 'input-glass', 'placeholder': 'Contexto, estrategia ou observacoes do ativo'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asset_class'].queryset = AssetClass.objects.filter(is_system=True).order_by('name')
        for field_name in ['ticker', 'rate_type', 'rate_value', 'maturity_date', 'invested_amount']:
            self.fields[field_name].required = False
        self.fields['quantity'].initial = 0
        self.fields['average_price'].initial = 0
        self.fields['current_price'].initial = 0
        self.fields['asset_class'].empty_label = 'Selecione a classe'
        self.fields['ownership'].widget.attrs.setdefault('class', 'input-glass')


class InvestmentTransactionForm(forms.ModelForm):
    class Meta:
        model = InvestmentTransaction
        fields = ['transaction_type', 'date', 'quantity', 'price', 'amount', 'fees', 'ir_withheld', 'broker', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = date.today
        for f in ['quantity', 'price', 'fees', 'ir_withheld', 'broker', 'notes']:
            self.fields[f].required = False


class InvestmentGoalForm(forms.ModelForm):
    class Meta:
        model = InvestmentGoal
        fields = ['name', 'asset_class', 'investment', 'target_amount', 'target_date', 'monthly_contribution', 'color']
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            self.fields['investment'].queryset = Investment.objects.filter(family_group=family_group, is_active=True)
        self.fields['asset_class'].queryset = AssetClass.objects.filter(is_system=True)
        self.fields['asset_class'].required = False
        self.fields['investment'].required = False
