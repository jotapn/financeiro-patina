def global_context(request):
    if not request.user.is_authenticated:
        return {}
    try:
        profile = request.user.profile
        group = profile.family_group
        members_count = group.members.count() if group else 1
        return {
            'user_profile': profile,
            'family_group': group,
            'family_members_count': members_count,
        }
    except Exception:
        return {}

