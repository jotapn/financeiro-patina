from django.contrib import admin

from .models import AiAssistantLog, ChatMessage, ChatSession


@admin.register(AiAssistantLog)
class AiAssistantLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__email', 'prompt', 'response')


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'created_at')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    search_fields = ('title', 'user__email')
    inlines = [ChatMessageInline]
