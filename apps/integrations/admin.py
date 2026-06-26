from django.contrib import admin

from .models import PluggyAccountLink, PluggyItem


class PluggyAccountLinkInline(admin.TabularInline):
    model = PluggyAccountLink
    extra = 0
    fields = ('name', 'pluggy_type', 'link_mode', 'financial_account', 'credit_card', 'is_active', 'last_synced_at')
    readonly_fields = ('last_synced_at',)


@admin.register(PluggyItem)
class PluggyItemAdmin(admin.ModelAdmin):
    list_display = ('connector_name', 'pluggy_item_id', 'family_group', 'status', 'is_active', 'last_synced_at')
    list_filter = ('status', 'is_active')
    search_fields = ('connector_name', 'pluggy_item_id')
    readonly_fields = ('created_at', 'updated_at', 'last_synced_at')
    inlines = [PluggyAccountLinkInline]


@admin.register(PluggyAccountLink)
class PluggyAccountLinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'pluggy_type', 'link_mode', 'financial_account', 'is_active', 'last_synced_at')
    list_filter = ('pluggy_type', 'link_mode', 'is_active')
    search_fields = ('name', 'pluggy_account_id')
    readonly_fields = ('created_at', 'updated_at', 'last_synced_at')
