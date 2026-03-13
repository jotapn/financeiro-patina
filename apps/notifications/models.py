from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = [
        ('budget', 'Orçamento'),
        ('bill', 'Fatura'),
        ('balance', 'Saldo'),
        ('goal', 'Meta'),
        ('portfolio', 'Carteira'),
        ('recurring', 'Recorrente'),
        ('info', 'Informação'),
    ]

    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    title = models.CharField(max_length=120)
    message = models.TextField()
    action_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
