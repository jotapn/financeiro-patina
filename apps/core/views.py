from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import FinancialAccount, PaymentMethod
from apps.transactions.models import Transaction

from .decorators import family_edit_required
from .forms import InviteForm, LoginForm, ProfileForm, RegisterForm
from .models import FamilyGroup, FamilyInvitation, UserProfile


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
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
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            if user:
                login(request, user)
                return redirect(request.GET.get('next', 'dashboard'))
            messages.error(request, 'E-mail ou senha incorretos.')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
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

    total_balance = sum(acc.current_balance for acc in accounts_qs if acc.include_in_total)

    recent_transactions = transactions_qs.select_related('category', 'account', 'user').order_by(
        '-date', '-created_at'
    )[:10]

    chart_data = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=i * 30)
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

    category_data = month_transactions.filter(transaction_type='expense').values(
        'category__name', 'category__color'
    ).annotate(total=Sum('amount')).order_by('-total')[:6]

    context = {
        'total_balance': total_balance,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'monthly_savings': monthly_income - monthly_expense,
        'accounts': accounts_qs[:5],
        'recent_transactions': recent_transactions,
        'chart_data': chart_data,
        'category_data': list(category_data),
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
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=user_profile)
    return render(request, 'core/profile.html', {'form': form})


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
    messages.success(request, f'Voc\u00ea entrou no grupo {inv.family_group.name}!')
    return redirect('dashboard')
