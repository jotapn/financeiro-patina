from apps.ai_assistant.services import get_model_status
from apps.notifications.models import Notification


def global_context(request):
    if not request.user.is_authenticated:
        return {}
    try:
        profile = request.user.profile
        group = profile.family_group
        members_count = group.members.count() if group else 1
        unread_notifications = Notification.objects.filter(user=request.user, is_read=False)[:5]
        return {
            'user_profile': profile,
            'family_group': group,
            'family_members_count': members_count,
            'unread_notifications': unread_notifications,
            'unread_notifications_count': unread_notifications.count(),
            'ai_model_status': get_model_status(),
        }
    except Exception:
        return {}
