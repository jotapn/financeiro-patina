from datetime import date

from django import forms

from .models import AssetClass, Investment, InvestmentGoal, InvestmentTransaction


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
        widgets = {
            'maturity_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asset_class'].queryset = AssetClass.objects.filter(is_system=True)
        for f in ['ticker', 'rate_type', 'rate_value', 'maturity_date', 'invested_amount']:
            self.fields[f].required = False
        self.fields['quantity'].initial = 0
        self.fields['average_price'].initial = 0
        self.fields['current_price'].initial = 0


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
