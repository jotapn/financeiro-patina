from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods

from apps.accounts.models import FinancialAccount, PaymentMethod
from apps.transactions.models import Transaction

from .decorators import family_edit_required
from .forms import InviteForm, LoginForm, ProfileForm, RegisterForm
from .models import FamilyGroup, FamilyInvitation, SecurityEvent, UserProfile
from .security import (
    audit_security_event,
    build_qr_code_data_url,
    confirmed_totp_device,
    get_setup_totp_device,
    hash_identifier,
    is_rate_limited,
    rate_limit_post,
    safe_next_url,
    user_must_configure_2fa,
    user_needs_2fa,
    user_requires_2fa,
    verify_and_login_otp,
)


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            if is_rate_limited(
                'register',
                request,
                limit=settings.RATE_LIMIT_REGISTER_LIMIT,
                window=settings.RATE_LIMIT_REGISTER_WINDOW,
                identifier=form.cleaned_data['email'],
            ):
                audit_security_event(request, SecurityEvent.RATE_LIMITED, metadata={'scope': 'register'})
                messages.error(request, 'Muitas tentativas. Tente novamente em instantes.')
                return render(request, 'registration/register.html', {'form': form}, status=429)
            user = form.save()
            group = FamilyGroup.objects.create(name=f'Fam\u00edlia de {user.first_name}')
            UserProfile.objects.create(user=user, family_group=group, role='admin')
            for name, mtype in [
                ('PIX', 'pix'),
                ('Dinheiro', 'cash'),
                ('D\u00e9bito', 'debit'),
                ('Cart\u00e3o de Cr\u00e9dito', 'credit'),
            ]:
                PaymentMethod.objects.create(
                    family_group=group,
                    name=name,
                    method_type=mtype,
                    is_default=(mtype == 'pix'),
                )
            login(request, user)
            messages.success(request, f'Bem-vindo ao FinanceFlow, {user.first_name}!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        if user_must_configure_2fa(request.user):
            return redirect('two_factor_setup')
        if user_needs_2fa(request.user):
            return redirect('two_factor_challenge')
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if is_rate_limited(
                'login',
                request,
                limit=settings.RATE_LIMIT_LOGIN_LIMIT,
                window=settings.RATE_LIMIT_LOGIN_WINDOW,
                identifier=email,
            ):
                audit_security_event(request, SecurityEvent.RATE_LIMITED, metadata={'scope': 'login', 'email': email})
                messages.error(request, 'Muitas tentativas. Tente novamente em instantes.')
                return render(request, 'registration/login.html', {'form': form}, status=429)
            user = authenticate(
                request,
                username=email,
                password=form.cleaned_data['password'],
            )
            if user:
                login(request, user)
                audit_security_event(request, SecurityEvent.LOGIN_SUCCESS, user=user)
                next_url = safe_next_url(request, request.GET.get('next'))
                if user_must_configure_2fa(user):
                    return redirect(f'{reverse("two_factor_setup")}?{urlencode({"next": next_url})}')
                if user_needs_2fa(user):
                    return redirect(f'{reverse("two_factor_challenge")}?{urlencode({"next": next_url})}')
                return redirect(next_url)
            audit_security_event(request, SecurityEvent.LOGIN_FAILURE, metadata={'email': email})
            messages.error(request, 'E-mail ou senha incorretos.')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def logout_view(request):
    if request.method == 'GET':
        messages.info(request, 'Use o botão de sair para encerrar a sessão com segurança.')
    if request.user.is_authenticated:
        audit_security_event(request, SecurityEvent.LOGOUT)
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    profile = request.user.profile
    group = profile.family_group
    today = date.today()
    view_mode = request.GET.get('view', 'personal')

    if view_mode == 'family' and group:
        transactions_qs = Transaction.objects.filter(family_group=group)
        accounts_qs = FinancialAccount.objects.filter(family_group=group, is_active=True)
    else:
        transactions_qs = Transaction.objects.filter(user=request.user)
        accounts_qs = FinancialAccount.objects.filter(owner=request.user, is_active=True)

    accounts = list(accounts_qs.with_current_balance())

    month_transactions = transactions_qs.filter(
        date__year=today.year,
        date__month=today.month,
        status='paid',
        is_ignored=False,
    )
    monthly_income = month_transactions.filter(transaction_type='income').aggregate(t=Sum('amount'))[
        't'
    ] or Decimal('0')
    monthly_expense = month_transactions.filter(transaction_type='expense').aggregate(t=Sum('amount'))[
        't'
    ] or Decimal('0')

    total_balance = sum(acc.current_balance for acc in accounts if acc.include_in_total)

    recent_transactions = transactions_qs.select_related('category', 'account', 'user').order_by(
        '-date', '-created_at'
    )[:10]

    chart_data = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - relativedelta(months=i)
        m_inc = transactions_qs.filter(
            date__year=month_date.year,
            date__month=month_date.month,
            transaction_type='income',
            status='paid',
        ).aggregate(t=Sum('amount'))['t'] or 0
        m_exp = transactions_qs.filter(
            date__year=month_date.year,
            date__month=month_date.month,
            transaction_type='expense',
            status='paid',
        ).aggregate(t=Sum('amount'))['t'] or 0
        chart_data.append({'month': month_date.strftime('%b'), 'income': float(m_inc), 'expense': float(m_exp)})

    category_data_qs = month_transactions.filter(transaction_type='expense').values(
        'category__name', 'category__color'
    ).annotate(total=Sum('amount')).order_by('-total')[:6]
    category_data = [
        {
            'category__name': item['category__name'],
            'category__color': item['category__color'],
            'total': float(item['total'] or 0),
        }
        for item in category_data_qs
    ]

    context = {
        'total_balance': total_balance,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'monthly_savings': monthly_income - monthly_expense,
        'accounts': accounts[:5],
        'recent_transactions': recent_transactions,
        'chart_data': chart_data,
        'category_data': category_data,
        'view_mode': view_mode,
        'today': today,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def profile(request):
    user_profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            audit_security_event(request, SecurityEvent.PROFILE_CHANGED)
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=user_profile)
    return render(
        request,
        'core/profile.html',
        {
            'form': form,
            'two_factor_enabled': confirmed_totp_device(request.user) is not None,
            'two_factor_required': request.user.is_staff or request.user.is_superuser,
        },
    )


@login_required
def family_settings(request):
    group = request.user.profile.family_group
    members = group.members.select_related('user').all() if group else []
    invitations = group.invitations.filter(accepted=False).all() if group else []
    return render(
        request,
        'core/family.html',
        {'group': group, 'members': members, 'invitations': invitations, 'invite_form': InviteForm()},
    )


@login_required
@family_edit_required
@rate_limit_post('family_invite')
def invite_member(request):
    if request.method == 'POST':
        form = InviteForm(request.POST)
        if form.is_valid():
            group = request.user.profile.family_group
            inv = FamilyInvitation.objects.create(
                family_group=group,
                email=form.cleaned_data['email'],
                invited_by=request.user,
            )
            audit_security_event(
                request,
                SecurityEvent.INVITE_CREATED,
                metadata={'invitation_id': inv.pk, 'email': inv.email},
            )
            messages.success(request, f'Convite enviado para {inv.email}!')
    return redirect('family')


@login_required
def accept_invite(request, token):
    inv = get_object_or_404(FamilyInvitation, token=token, accepted=False)
    if inv.is_expired:
        messages.error(request, 'Este convite expirou.')
        return redirect('dashboard')
    user_profile = request.user.profile
    user_profile.family_group = inv.family_group
    user_profile.role = 'member'
    user_profile.save()
    inv.accepted = True
    inv.save()
    audit_security_event(
        request,
        SecurityEvent.INVITE_ACCEPTED,
        metadata={'invitation_id': inv.pk, 'family_group_id': inv.family_group_id},
    )
    messages.success(request, f'Voc\u00ea entrou no grupo {inv.family_group.name}!')
    return redirect('dashboard')


@login_required
def two_factor_setup(request):
    next_url = safe_next_url(request, request.GET.get('next') or request.POST.get('next'))
    if confirmed_totp_device(request.user) and not user_must_configure_2fa(request.user):
        messages.info(request, '2FA já está ativo.')
        return redirect('profile')

    device = get_setup_totp_device(request.user)
    if request.method == 'POST':
        if is_rate_limited(
            '2fa_setup',
            request,
            limit=settings.RATE_LIMIT_2FA_LIMIT,
            window=settings.RATE_LIMIT_2FA_WINDOW,
        ):
            audit_security_event(request, SecurityEvent.RATE_LIMITED, metadata={'scope': '2fa_setup'})
            messages.error(request, 'Muitas tentativas. Tente novamente em instantes.')
            return render(
                request,
                'core/two_factor_setup.html',
                {'qr_code_data_url': build_qr_code_data_url(device), 'next': next_url},
                status=429,
            )
        token = request.POST.get('token', '')
        if verify_and_login_otp(request, device, token):
            device.confirmed = True
            device.save(update_fields=['confirmed'])
            audit_security_event(request, SecurityEvent.TWO_FACTOR_ENABLED)
            messages.success(request, '2FA ativado com sucesso.')
            return redirect(next_url)
        audit_security_event(request, SecurityEvent.TWO_FACTOR_FAILURE)
        messages.error(request, 'Código inválido ou expirado. Confira o app autenticador e tente novamente.')

    return render(
        request,
        'core/two_factor_setup.html',
        {'qr_code_data_url': build_qr_code_data_url(device), 'next': next_url},
    )


@login_required
def two_factor_challenge(request):
    next_url = safe_next_url(request, request.GET.get('next') or request.POST.get('next'))
    if user_must_configure_2fa(request.user):
        return redirect(f'{reverse("two_factor_setup")}?{urlencode({"next": next_url})}')
    if not user_requires_2fa(request.user) or not user_needs_2fa(request.user):
        return redirect(next_url)

    device = confirmed_totp_device(request.user)
    if request.method == 'POST':
        if is_rate_limited(
            '2fa_challenge',
            request,
            limit=settings.RATE_LIMIT_2FA_LIMIT,
            window=settings.RATE_LIMIT_2FA_WINDOW,
        ):
            audit_security_event(request, SecurityEvent.RATE_LIMITED, metadata={'scope': '2fa_challenge'})
            messages.error(request, 'Muitas tentativas. Tente novamente em instantes.')
            return render(request, 'registration/two_factor_challenge.html', {'next': next_url}, status=429)
        token = request.POST.get('token', '')
        if verify_and_login_otp(request, device, token):
            audit_security_event(request, SecurityEvent.TWO_FACTOR_SUCCESS)
            return redirect(next_url)
        audit_security_event(request, SecurityEvent.TWO_FACTOR_FAILURE)
        messages.error(request, 'Código inválido ou expirado. Confira o app autenticador e tente novamente.')

    return render(request, 'registration/two_factor_challenge.html', {'next': next_url})


@login_required
def two_factor_disable(request):
    if request.method != 'POST':
        return redirect('profile')
    if request.user.is_staff or request.user.is_superuser:
        messages.error(request, '2FA é obrigatório para admins internos.')
        return redirect('profile')
    request.user.totpdevice_set.filter(confirmed=True).delete()
    audit_security_event(request, SecurityEvent.TWO_FACTOR_DISABLED)
    messages.success(request, '2FA desativado.')
    return redirect('profile')


class FinancePasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.txt'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('core_password_reset_done')
    extra_email_context = {'reset_confirm_url_name': 'core_password_reset_confirm'}

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip().lower()
        if is_rate_limited(
            'password_reset',
            request,
            limit=settings.RATE_LIMIT_PASSWORD_RESET_LIMIT,
            window=settings.RATE_LIMIT_PASSWORD_RESET_WINDOW,
            identifier=email or None,
        ):
            audit_security_event(
                request,
                SecurityEvent.RATE_LIMITED,
                metadata={'scope': 'password_reset', 'email_hash': hash_identifier(email)},
            )
            messages.error(request, 'Muitas tentativas. Tente novamente em instantes.')
            return render(request, self.template_name, {'form': self.get_form()}, status=429)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get('email', '')
        audit_security_event(
            self.request,
            SecurityEvent.PASSWORD_RESET_REQUESTED,
            metadata={'email_hash': hash_identifier(email)},
        )
        return super().form_valid(form)


class FinancePasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'


class FinancePasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('core_password_reset_complete')

    def form_valid(self, form):
        audit_security_event(
            self.request,
            SecurityEvent.PASSWORD_RESET_SUCCESS,
            user=self.user,
            metadata={'user_id': self.user.pk},
        )
        return super().form_valid(form)


class FinancePasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'
