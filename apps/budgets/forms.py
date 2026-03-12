from datetime import date

from django import forms
from django.db.models import Q

from apps.accounts.models import FinancialAccount
from apps.categories.models import Category

from .models import Budget, FinancialGoal


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount', 'period', 'scope', 'reference_month', 'alert_threshold', 'rollover']
        widgets = {
            'reference_month': forms.DateInput(attrs={'type': 'month'}, format='%Y-%m'),
        }

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            self.fields['category'].queryset = Category.objects.filter(
                Q(family_group=family_group) | Q(is_system=True), category_type='expense'
            ).order_by('name')
        self.fields['reference_month'].initial = date.today().replace(day=1)


class GoalForm(forms.ModelForm):
    class Meta:
        model = FinancialGoal
        fields = [
            'name',
            'goal_type',
            'scope',
            'target_amount',
            'current_amount',
            'target_date',
            'linked_account',
            'monthly_contribution',
            'color',
            'icon',
        ]
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            self.fields['linked_account'].queryset = FinancialAccount.objects.filter(
                family_group=family_group, is_active=True
            )
        self.fields['linked_account'].required = False


class ContributionForm(forms.Form):
    amount = forms.DecimalField(max_digits=15, decimal_places=2, label='Valor do aporte')
    date = forms.DateField(initial=date.today, widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    account = forms.ModelChoiceField(queryset=FinancialAccount.objects.none(), required=False, label='Débitar da conta')
    notes = forms.CharField(max_length=200, required=False, label='Observação')

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            self.fields['account'].queryset = FinancialAccount.objects.filter(
                family_group=family_group, is_active=True
            )
