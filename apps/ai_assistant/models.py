from django.db import models


class AiAssistantLog(models.Model):
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='ai_logs')
    prompt = models.TextField()
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

