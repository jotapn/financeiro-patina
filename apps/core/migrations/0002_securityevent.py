# Generated for SaaS security hardening.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SecurityEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'event_type',
                    models.CharField(
                        choices=[
                            ('login_success', 'Login bem-sucedido'),
                            ('login_failure', 'Falha de login'),
                            ('logout', 'Logout'),
                            ('invite_created', 'Convite criado'),
                            ('invite_accepted', 'Convite aceito'),
                            ('profile_changed', 'Perfil alterado'),
                            ('permission_changed', 'Permissao alterada'),
                            ('rate_limited', 'Rate limit aplicado'),
                            ('two_factor_enabled', '2FA ativado'),
                            ('two_factor_disabled', '2FA desativado'),
                            ('two_factor_success', '2FA verificado'),
                            ('two_factor_failure', 'Falha de 2FA'),
                            ('password_reset_requested', 'Recuperacao de senha solicitada'),
                            ('password_reset_success', 'Senha redefinida'),
                        ],
                        max_length=50,
                    ),
                ),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='security_events',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Evento de seguranca',
                'verbose_name_plural': 'Eventos de seguranca',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['event_type', 'created_at'], name='core_securi_event_t_922070_idx'),
                    models.Index(fields=['user', 'created_at'], name='core_securi_user_id_29d34d_idx'),
                ],
            },
        ),
    ]
