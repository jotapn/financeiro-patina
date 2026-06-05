from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import family_edit_required
from apps.core.security import rate_limit_post

from .forms import InvestmentForm, InvestmentGoalForm, InvestmentTransactionForm
from .models import AssetClass, Investment, InvestmentGoal


@login_required
def portfolio_dashboard(request):
    group = request.user.profile.family_group
    view_mode = request.GET.get('view', 'personal')

    if view_mode == 'family':
        investments = Investment.objects.filter(family_group=group, is_active=True)
    else:
        investments = Investment.objects.filter(owner=request.user, is_active=True)

    investments = investments.select_related('asset_class')

    total_invested = sum(inv.total_invested for inv in investments)
    total_current = sum(inv.current_value for inv in investments)
    total_profit = total_current - total_invested
    total_profit_pct = (total_profit / total_invested * 100) if total_invested > 0 else Decimal('0')
    total_dividends = sum(inv.total_dividends for inv in investments)

    allocation = {}
    for inv in investments:
        class_name = inv.asset_class.name if inv.asset_class else 'Sem classe'
        class_color = inv.asset_class.color if inv.asset_class else '#94a3b8'
        allocation[class_name] = allocation.get(
            class_name,
            {
                'name': class_name,
                'color': class_color,
                'total': Decimal('0'),
            },
        )
        allocation[class_name]['total'] += inv.current_value

    allocation_list = sorted(allocation.values(), key=lambda x: x['total'], reverse=True)
    if total_current > 0:
        for item in allocation_list:
            item['pct'] = round(float(item['total'] / total_current * 100), 1)
    else:
        for item in allocation_list:
            item['pct'] = 0

    variable = [i for i in investments if i.is_variable_income and i.total_invested > 0]
    top_gainers = sorted(variable, key=lambda x: x.profit_loss_pct, reverse=True)[:3]
    top_losers = sorted(variable, key=lambda x: x.profit_loss_pct)[:3]

    goals = InvestmentGoal.objects.filter(family_group=group, owner=request.user, is_completed=False).select_related(
        'asset_class', 'investment'
    )

    context = {
        'investments': investments,
        'total_invested': total_invested,
        'total_current': total_current,
        'total_profit': total_profit,
        'total_profit_pct': total_profit_pct,
        'total_dividends': total_dividends,
        'allocation_list': allocation_list,
        'allocation_json': [
            {'name': a['name'], 'value': float(a['total']), 'color': a['color']}
            for a in allocation_list
        ],
        'top_gainers': top_gainers,
        'top_losers': top_losers,
        'goals': goals,
        'view_mode': view_mode,
    }
    return render(request, 'investments/dashboard.html', context)


@login_required
def investment_list(request):
    group = request.user.profile.family_group
    asset_type = request.GET.get('type')
    view_mode = request.GET.get('view', 'personal')

    if view_mode == 'family':
        qs = Investment.objects.filter(family_group=group, is_active=True)
    else:
        qs = Investment.objects.filter(owner=request.user, is_active=True)

    if asset_type:
        qs = qs.filter(asset_class__asset_type=asset_type)

    qs = qs.select_related('asset_class', 'owner').order_by('-current_value')
    asset_classes = AssetClass.objects.filter(is_system=True)

    return render(
        request,
        'investments/list.html',
        {
            'investments': qs,
            'asset_classes': asset_classes,
            'current_type': asset_type,
            'view_mode': view_mode,
        },
    )


def _investment_list_context(request, *, form=None, show_modal=False):
    group = request.user.profile.family_group
    asset_type = request.GET.get('type')
    view_mode = request.GET.get('view', 'personal')

    if view_mode == 'family':
        qs = Investment.objects.filter(family_group=group, is_active=True)
    else:
        qs = Investment.objects.filter(owner=request.user, is_active=True)

    if asset_type:
        qs = qs.filter(asset_class__asset_type=asset_type)

    qs = qs.select_related('asset_class', 'owner').order_by('-current_value')
    asset_classes = AssetClass.objects.filter(is_system=True)

    return {
        'investments': qs,
        'asset_classes': asset_classes,
        'current_type': asset_type,
        'view_mode': view_mode,
        'form': form,
        'show_modal': show_modal,
    }


@login_required
@family_edit_required
@rate_limit_post('investment_create')
def investment_create(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = InvestmentForm(request.POST)
        if form.is_valid():
            inv = form.save(commit=False)
            inv.owner = request.user
            inv.family_group = group
            inv.save()
            inv.initialize_snapshot()
            messages.success(request, f'Investimento "{inv.name}" cadastrado!')
            return redirect('investment_detail', pk=inv.pk)
    else:
        form = InvestmentForm()

    return render(request, 'investments/list.html', _investment_list_context(request, form=form, show_modal=True))


@login_required
def investment_detail(request, pk):
    group = request.user.profile.family_group
    inv = get_object_or_404(Investment, pk=pk, family_group=group)
    transactions = inv.transactions.order_by('-date')
    dividends = inv.transactions.filter(transaction_type__in=('dividend', 'jcp', 'income')).order_by('-date')
    tx_form = InvestmentTransactionForm()

    return render(
        request,
        'investments/detail.html',
        {
            'investment': inv,
            'transactions': transactions,
            'dividends': dividends,
            'tx_form': tx_form,
        },
    )


@login_required
@family_edit_required
@rate_limit_post('investment_add_transaction')
def investment_add_transaction(request, pk):
    group = request.user.profile.family_group
    inv = get_object_or_404(Investment, pk=pk, family_group=group)

    if request.method == 'POST':
        form = InvestmentTransactionForm(request.POST)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.investment = inv
            tx.save()
            messages.success(request, 'Transação registrada e portfólio atualizado!')
    return redirect('investment_detail', pk=pk)


@login_required
@family_edit_required
@rate_limit_post('investment_goal_create')
def investment_goal_create(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = InvestmentGoalForm(request.POST, family_group=group)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.owner = request.user
            goal.family_group = group
            goal.save()
            messages.success(request, f'Meta de investimento "{goal.name}" criada!')
    return redirect('portfolio_dashboard')


@login_required
@family_edit_required
@rate_limit_post('investment_refresh_prices')
def refresh_prices(request):
    from .tasks import update_crypto_prices, update_stock_prices

    update_stock_prices.delay()
    update_crypto_prices.delay()
    messages.success(request, 'Atualização de cotações iniciada! Aguarde alguns instantes.')
    return redirect('portfolio_dashboard')
