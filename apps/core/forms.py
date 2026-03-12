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


class InviteForm(forms.Form):
    email = forms.EmailField(label='E-mail do convidado')

