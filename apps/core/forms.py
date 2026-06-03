from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True, label='Nome')
    last_name = forms.CharField(max_length=50, required=True, label='Sobrenome')

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label='E-mail')
    password = forms.CharField(widget=forms.PasswordInput, label='Senha')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'avatar',
            'default_currency',
            'timezone',
            'financial_month_start_day',
            'monthly_income',
            'notify_budget_alert',
            'notify_bill_due',
            'notify_low_balance',
            'low_balance_threshold',
            'budget_alert_threshold',
            'bill_due_days_ahead',
        ]
        labels = {
            'avatar': 'Avatar',
            'default_currency': 'Moeda padrao',
            'timezone': 'Fuso horario',
            'financial_month_start_day': 'Inicio do mes financeiro',
            'monthly_income': 'Renda mensal',
            'notify_budget_alert': 'Alertas de orcamento',
            'notify_bill_due': 'Lembretes de fatura',
            'notify_low_balance': 'Alertas de saldo baixo',
            'low_balance_threshold': 'Valor minimo para alerta',
            'budget_alert_threshold': 'Alerta de orcamento em (%)',
            'bill_due_days_ahead': 'Avisar fatura com antecedencia (dias)',
        }
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'class': 'input-glass'}),
            'default_currency': forms.Select(attrs={'class': 'input-glass'}),
            'timezone': forms.TextInput(attrs={'class': 'input-glass', 'placeholder': 'Ex.: America/Sao_Paulo'}),
            'financial_month_start_day': forms.NumberInput(
                attrs={'class': 'input-glass', 'min': '1', 'max': '31', 'placeholder': '1'}
            ),
            'monthly_income': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'notify_budget_alert': forms.CheckboxInput(attrs={'class': 'toggle-input'}),
            'notify_bill_due': forms.CheckboxInput(attrs={'class': 'toggle-input'}),
            'notify_low_balance': forms.CheckboxInput(attrs={'class': 'toggle-input'}),
            'low_balance_threshold': forms.NumberInput(
                attrs={'class': 'input-glass input-with-prefix', 'placeholder': '0.00', 'step': '0.01'}
            ),
            'budget_alert_threshold': forms.NumberInput(
                attrs={'class': 'input-glass', 'min': '1', 'max': '100', 'placeholder': '80'}
            ),
            'bill_due_days_ahead': forms.NumberInput(
                attrs={'class': 'input-glass', 'min': '0', 'max': '30', 'placeholder': '3'}
            ),
        }


class InviteForm(forms.Form):
    email = forms.EmailField(label='E-mail do convidado')

