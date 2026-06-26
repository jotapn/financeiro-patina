from apps.accounts.models import PaymentMethod
from apps.core.models import FamilyGroup, UserProfile
from apps.core.security import user_must_configure_2fa, user_needs_2fa


TWO_FACTOR_ALLOWED_PATH_PREFIXES = (
    '/auth/login/',
    '/auth/logout/',
    '/auth/password-reset/',
    '/auth/reset/',
    '/profile/2fa/',
    '/static/',
    '/media/',
)


class EnsureUserProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'admin'},
            )
            if profile.family_group is None:
                owner_name = user.first_name or user.email.split('@')[0]
                group = FamilyGroup.objects.create(name=f'Fam\u00edlia de {owner_name}')
                profile.family_group = group
                profile.save(update_fields=['family_group'])
                for name, mtype in [
                    ('PIX', 'pix'),
                    ('Dinheiro', 'cash'),
                    ('D\u00e9bito', 'debit'),
                    ('Cart\u00e3o de Cr\u00e9dito', 'credit'),
                ]:
                    PaymentMethod.objects.get_or_create(
                        family_group=group,
                        name=name,
                        defaults={'method_type': mtype, 'is_default': (mtype == 'pix')},
                    )
            elif profile.family_group is not None:
                for name, mtype in [
                    ('PIX', 'pix'),
                    ('Dinheiro', 'cash'),
                    ('D\u00e9bito', 'debit'),
                    ('Cart\u00e3o de Cr\u00e9dito', 'credit'),
                ]:
                    PaymentMethod.objects.get_or_create(
                        family_group=profile.family_group,
                        method_type=mtype,
                        defaults={'name': name, 'is_default': (mtype == 'pix')},
                    )

        response = self.get_response(request)
        return response


class RequireTwoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path_info
        if user and user.is_authenticated and not self._is_allowed_path(path):
            if user_must_configure_2fa(user):
                from django.shortcuts import redirect

                return redirect('two_factor_setup')
            if user_needs_2fa(user):
                from django.shortcuts import redirect

                return redirect('two_factor_challenge')

        return self.get_response(request)

    def _is_allowed_path(self, path):
        return any(path.startswith(prefix) for prefix in TWO_FACTOR_ALLOWED_PATH_PREFIXES)
