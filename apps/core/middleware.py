from apps.accounts.models import PaymentMethod
from apps.core.models import FamilyGroup, UserProfile


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
                group = FamilyGroup.objects.create(name=f'Família de {owner_name}')
                profile.family_group = group
                profile.save(update_fields=['family_group'])
                for name, mtype in [('PIX', 'pix'), ('Dinheiro', 'cash'), ('Débito', 'debit')]:
                    PaymentMethod.objects.get_or_create(
                        family_group=group,
                        name=name,
                        defaults={'method_type': mtype, 'is_default': (mtype == 'pix')},
                    )

        response = self.get_response(request)
        return response
