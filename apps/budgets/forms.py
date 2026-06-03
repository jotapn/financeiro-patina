from datetime import date

from django import forms
from django.db.models import Q

from apps.accounts.models import FinancialAccount
from apps.categories.models import Category

from .models import Budget, FinancialGoal

GOAL_ICON_CHOICES = [
    ('target', 'Alvo'),
    ('piggy-bank', 'Cofrinho'),
    ('shield', 'Protecao'),
    ('plane', 'Viagem'),
    ('home', 'Casa'),
    ('car', 'Carro'),
    ('briefcase', 'Trabalho'),
    ('graduation-cap', 'Educacao'),
    ('heart', 'Saude'),
    ('gem', 'Patrimonio'),
    ('wallet', 'Carteira'),
    ('badge-dollar-sign', 'Financeiro'),
]


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount', 'period', 'scope', 'reference_month', 'alert_threshold', 'rollover']
        labels = {
            'category': 'Categoria',
            'amount': 'Limite do orcamento',
            'period': 'Periodicidade',
            'scope': 'Abrangencia',
            'reference_month': 'Mes de referencia',
            'alert_threshold': 'Alerta em (%)',
            'rollover': 'Acumular saldo restante',
        }
        widgets = {
            'category': forms.Select(attrs={'class': 'input-glass'}),
            'amount': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'period': forms.Select(attrs={'class': 'input-glass'}),
            'scope': forms.Select(attrs={'class': 'input-glass'}),
            'reference_month': forms.DateInput(attrs={'type': 'month', 'class': 'input-glass'}, format='%Y-%m'),
            'alert_threshold': forms.NumberInput(
                attrs={'class': 'input-glass', 'placeholder': '80', 'min': '1', 'max': '100'}
            ),
            'rollover': forms.CheckboxInput(attrs={'class': 'toggle-input'}),
        }

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            self.fields['category'].queryset = Category.objects.filter(
                Q(family_group=family_group) | Q(is_system=True), category_type='expense'
            ).order_by('name')
        self.fields['reference_month'].initial = date.today().replace(day=1)
        self.fields['category'].empty_label = 'Selecione a categoria'


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
        labels = {
            'name': 'Nome da meta',
            'goal_type': 'Tipo de meta',
            'scope': 'Abrangencia',
            'target_amount': 'Valor alvo',
            'current_amount': 'Valor inicial',
            'target_date': 'Data alvo',
            'linked_account': 'Conta vinculada',
            'monthly_contribution': 'Contribuicao mensal planejada',
            'color': 'Cor de destaque',
            'icon': 'Icone',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input-glass', 'placeholder': 'Ex.: Reserva de emergencia'}),
            'goal_type': forms.Select(attrs={'class': 'input-glass'}),
            'scope': forms.Select(attrs={'class': 'input-glass'}),
            'target_amount': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'current_amount': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'target_date': forms.DateInput(attrs={'type': 'date', 'class': 'input-glass'}, format='%Y-%m-%d'),
            'linked_account': forms.Select(attrs={'class': 'input-glass'}),
            'monthly_contribution': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'color': forms.TextInput(attrs={'type': 'color'}),
            'icon': forms.Select(attrs={'class': 'input-glass'}),
        }

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if family_group:
            self.fields['linked_account'].queryset = FinancialAccount.objects.filter(
                family_group=family_group, is_active=True
            ).order_by('name')
        self.fields['linked_account'].required = False
        self.fields['linked_account'].empty_label = 'Sem conta vinculada'
        self.fields['icon'].widget.choices = GOAL_ICON_CHOICES


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
