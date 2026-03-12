from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import FamilyGroup, FamilyInvitation, User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_active')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informações pessoais', {'fields': ('first_name', 'last_name', 'username')}),
        (
            'Permissões',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        ('Datas importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
            },
        ),
    )


@admin.register(FamilyGroup)
class FamilyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'family_group', 'role')


@admin.register(FamilyInvitation)
class FamilyInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'family_group', 'accepted', 'expires_at')

