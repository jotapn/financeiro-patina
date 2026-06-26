from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import SecurityEvent, User, UserProfile


@receiver(pre_save, sender=User)
def remember_user_security_fields(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_security_fields = None
        return
    previous = sender.objects.filter(pk=instance.pk).values(
        'is_staff',
        'is_superuser',
        'is_active',
    ).first()
    instance._previous_security_fields = previous


@receiver(post_save, sender=User)
def audit_user_permission_changes(sender, instance, created, **kwargs):
    previous = getattr(instance, '_previous_security_fields', None)
    if created or previous is None:
        return
    current = {
        'is_staff': instance.is_staff,
        'is_superuser': instance.is_superuser,
        'is_active': instance.is_active,
    }
    changed = {key: current[key] for key in current if previous.get(key) != current[key]}
    if changed:
        SecurityEvent.objects.create(
            user=instance,
            event_type=SecurityEvent.PERMISSION_CHANGED,
            metadata={'changed_fields': ','.join(sorted(changed))},
        )


@receiver(pre_save, sender=UserProfile)
def remember_profile_role(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_role = None
        return
    previous = sender.objects.filter(pk=instance.pk).values('role').first()
    instance._previous_role = previous['role'] if previous else None


@receiver(post_save, sender=UserProfile)
def audit_profile_role_changes(sender, instance, created, **kwargs):
    previous_role = getattr(instance, '_previous_role', None)
    if created or previous_role is None or previous_role == instance.role:
        return
    SecurityEvent.objects.create(
        user=instance.user,
        event_type=SecurityEvent.PERMISSION_CHANGED,
        metadata={'profile_role': instance.role},
    )
