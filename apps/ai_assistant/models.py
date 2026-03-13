from django.db import models


class AiAssistantLog(models.Model):
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='ai_logs')
    prompt = models.TextField()
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ChatSession(models.Model):
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sessão de Chat'
        verbose_name_plural = 'Sessões de Chat'

    def save(self, *args, **kwargs):
        if not self.title and self.pk:
            first_message = self.messages.filter(role='user').order_by('created_at').first()
            if first_message:
                self.title = first_message.content[:50]
        super().save(*args, **kwargs)

    def sync_title(self):
        first_message = self.messages.filter(role='user').order_by('created_at').first()
        if first_message:
            self.title = first_message.content[:50]
            self.save(update_fields=['title'])

    def __str__(self):
        return self.title or f'Conversa {self.pk}'


class ChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'Usuário'), ('assistant', 'Assistente')]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Mensagem de Chat'
        verbose_name_plural = 'Mensagens de Chat'

    def __str__(self):
        return f'{self.get_role_display()} - {self.session_id}'
