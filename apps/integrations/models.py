from django.db import models

from .fields import EncryptedTextField


class PluggyItem(models.Model):
    """Uma conexão Open Finance (item Pluggy) entre uma instituição e a família.

    Um *item* pode expor vários *accounts* (corrente, poupança, cartão), cada um
    representado por um :class:`PluggyAccountLink`.
    """

    STATUS_PENDING = 'pending'
    STATUS_UPDATING = 'updating'
    STATUS_UPDATED = 'updated'
    STATUS_PARTIAL = 'partial_success'
    STATUS_LOGIN_ERROR = 'login_error'
    STATUS_OUTDATED = 'outdated'
    STATUS_WAITING_USER = 'waiting_user_input'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendente'),
        (STATUS_UPDATING, 'Atualizando'),
        (STATUS_UPDATED, 'Atualizado'),
        (STATUS_PARTIAL, 'Sucesso parcial'),
        (STATUS_LOGIN_ERROR, 'Erro de login'),
        (STATUS_OUTDATED, 'Desatualizado'),
        (STATUS_WAITING_USER, 'Aguardando usuário'),
        (STATUS_ERROR, 'Erro'),
    ]

    family_group = models.ForeignKey(
        'core.FamilyGroup', on_delete=models.CASCADE, related_name='pluggy_items'
    )
    owner = models.ForeignKey(
        'core.User', on_delete=models.CASCADE, related_name='pluggy_items'
    )
    pluggy_item_id = models.CharField(max_length=64, unique=True)
    connector_id = models.IntegerField(null=True, blank=True)
    connector_name = models.CharField(max_length=120, blank=True)
    connector_image_url = models.URLField(blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_PENDING)
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Conexão Pluggy'
        verbose_name_plural = 'Conexões Pluggy'

    def __str__(self):
        return f'{self.connector_name or "Item"} ({self.pluggy_item_id})'


class PluggyAccountLink(models.Model):
    """Mapeia um *account* do Pluggy para uma conta/cartão interno."""

    TYPE_BANK = 'BANK'
    TYPE_CREDIT = 'CREDIT'
    TYPE_CHOICES = [
        (TYPE_BANK, 'Conta bancária'),
        (TYPE_CREDIT, 'Cartão de crédito'),
    ]

    MODE_CREATED = 'created'
    MODE_MAPPED = 'mapped'
    MODE_IGNORED = 'ignored'
    MODE_PENDING = 'pending'
    MODE_CHOICES = [
        (MODE_PENDING, 'Aguardando decisão'),
        (MODE_CREATED, 'Conta criada'),
        (MODE_MAPPED, 'Vinculada a conta existente'),
        (MODE_IGNORED, 'Ignorada'),
    ]

    item = models.ForeignKey(PluggyItem, on_delete=models.CASCADE, related_name='account_links')
    pluggy_account_id = models.CharField(max_length=64, unique=True)
    pluggy_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_BANK)
    pluggy_subtype = models.CharField(max_length=40, blank=True)
    name = models.CharField(max_length=160, blank=True)
    number_masked = EncryptedTextField(blank=True, default='')
    pluggy_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency_code = models.CharField(max_length=3, default='BRL')

    financial_account = models.ForeignKey(
        'accounts.FinancialAccount',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='pluggy_links',
    )
    # Fase 2: vínculo de cartão de crédito.
    credit_card = models.ForeignKey(
        'cards.CreditCard',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='pluggy_links',
    )

    link_mode = models.CharField(max_length=10, choices=MODE_CHOICES, default=MODE_PENDING)
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Vínculo de conta Pluggy'
        verbose_name_plural = 'Vínculos de conta Pluggy'

    def __str__(self):
        return f'{self.name or self.pluggy_account_id} -> {self.link_mode}'

    @property
    def target(self):
        return self.financial_account or self.credit_card
