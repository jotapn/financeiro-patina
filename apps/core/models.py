import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return self.get_full_name() or self.email


class FamilyGroup(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nome do grupo')
    invite_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Grupo Familiar'
        verbose_name_plural = 'Grupos Familiares'

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('member', 'Membro'),
        ('viewer', 'Visualizador'),
    ]
    CURRENCY_CHOICES = [('BRL', 'R$ Real'), ('USD', 'US$ Dólar'), ('EUR', '€ Euro')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    family_group = models.ForeignKey(
        FamilyGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='members',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='admin')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    default_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='BRL')
    timezone = models.CharField(max_length=50, default='America/Sao_Paulo')
    financial_month_start_day = models.IntegerField(default=1)
    monthly_income = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notify_budget_alert = models.BooleanField(default=True)
    notify_bill_due = models.BooleanField(default=True)
    notify_low_balance = models.BooleanField(default=True)
    low_balance_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    budget_alert_threshold = models.IntegerField(default=80)
    bill_due_days_ahead = models.IntegerField(default=3)

    class Meta:
        verbose_name = 'Perfil'

    def __str__(self):
        return f'Perfil de {self.user.get_full_name()}'

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def can_edit(self):
        return self.role in ('admin', 'member')


class FamilyInvitation(models.Model):
    family_group = models.ForeignKey(
        FamilyGroup, on_delete=models.CASCADE, related_name='invitations'
    )
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    invited_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_invitations'
    )
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Convite'

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f'Convite para {self.email}'


class SecurityEvent(models.Model):
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILURE = 'login_failure'
    LOGOUT = 'logout'
    INVITE_CREATED = 'invite_created'
    INVITE_ACCEPTED = 'invite_accepted'
    PROFILE_CHANGED = 'profile_changed'
    PERMISSION_CHANGED = 'permission_changed'
    RATE_LIMITED = 'rate_limited'
    TWO_FACTOR_ENABLED = 'two_factor_enabled'
    TWO_FACTOR_DISABLED = 'two_factor_disabled'
    TWO_FACTOR_SUCCESS = 'two_factor_success'
    TWO_FACTOR_FAILURE = 'two_factor_failure'
    PASSWORD_RESET_REQUESTED = 'password_reset_requested'
    PASSWORD_RESET_SUCCESS = 'password_reset_success'

    EVENT_CHOICES = [
        (LOGIN_SUCCESS, 'Login bem-sucedido'),
        (LOGIN_FAILURE, 'Falha de login'),
        (LOGOUT, 'Logout'),
        (INVITE_CREATED, 'Convite criado'),
        (INVITE_ACCEPTED, 'Convite aceito'),
        (PROFILE_CHANGED, 'Perfil alterado'),
        (PERMISSION_CHANGED, 'Permissao alterada'),
        (RATE_LIMITED, 'Rate limit aplicado'),
        (TWO_FACTOR_ENABLED, '2FA ativado'),
        (TWO_FACTOR_DISABLED, '2FA desativado'),
        (TWO_FACTOR_SUCCESS, '2FA verificado'),
        (TWO_FACTOR_FAILURE, 'Falha de 2FA'),
        (PASSWORD_RESET_REQUESTED, 'Recuperacao de senha solicitada'),
        (PASSWORD_RESET_SUCCESS, 'Senha redefinida'),
    ]

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='security_events',
    )
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
        verbose_name = 'Evento de seguranca'
        verbose_name_plural = 'Eventos de seguranca'

    def __str__(self):
        return f'{self.event_type} em {self.created_at:%Y-%m-%d %H:%M:%S}'

