from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def family_edit_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if not profile or not profile.can_edit:
            messages.error(request, 'Seu perfil não tem permissão para alterar dados da família.')
            return redirect(request.META.get('HTTP_REFERER') or 'dashboard')
        return view_func(request, *args, **kwargs)

    return wrapped
