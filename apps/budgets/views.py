from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.categories.models import Category
from apps.core.decorators import family_edit_required
from apps.transactions.models import Transaction

from .forms import BudgetForm, ContributionForm, GoalForm
from .models import Budget, FinancialGoal, GoalContribution


def _get_transfer_category():
    return Category.objects.filter(name='Transfer\u00eancia', is_system=True).first() or Category.objects.filter(
        is_system=True
    ).first()


@login_required
def budget_list(request):
    group = request.user.profile.family_group
    today = date.today()
    ref = today.replace(day=1)

    budgets = Budget.objects.filter(family_group=group, reference_month=ref).select_related('category')
    goals = FinancialGoal.objects.filter(family_group=group, is_completed=False).select_related('linked_account')

    return render(
        request,
        'budgets/list.html',
        {
            'budgets': budgets,
            'goals': goals,
            'ref_month': ref,
        },
    )


@login_required
@family_edit_required
def budget_create(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = BudgetForm(request.POST, family_group=group)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.owner = request.user
            budget.family_group = group
            budget.save()
            messages.success(request, 'Or\u00e7amento criado!')
            return redirect('budget_list')
    else:
        form = BudgetForm(family_group=group)

    budgets = Budget.objects.filter(family_group=group, reference_month=date.today().replace(day=1)).select_related(
        'category'
    )
    goals = FinancialGoal.objects.filter(family_group=group, is_completed=False).select_related('linked_account')
    return render(
        request,
        'budgets/list.html',
        {'form': form, 'show_modal': True, 'budgets': budgets, 'goals': goals, 'ref_month': date.today().replace(day=1)},
    )


@login_required
@family_edit_required
def budget_clone(request):
    group = request.user.profile.family_group
    today = date.today()
    current = today.replace(day=1)
    previous = current - relativedelta(months=1)

    prev_budgets = Budget.objects.filter(
        family_group=group,
        owner=request.user,
        reference_month=previous,
    )
    created = 0
    for b in prev_budgets:
        _, is_new = Budget.objects.get_or_create(
            owner=request.user,
            family_group=group,
            category=b.category,
            reference_month=current,
            scope=b.scope,
            defaults={'amount': b.amount, 'period': b.period, 'alert_threshold': b.alert_threshold},
        )
        if is_new:
            created += 1

    messages.success(request, f'{created} or\u00e7amento(s) copiado(s) do m\u00eas anterior!')
    return redirect('budget_list')


@login_required
@family_edit_required
def goal_create(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = GoalForm(request.POST, family_group=group)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.owner = request.user
            goal.family_group = group
            goal.save()
            messages.success(request, f'Meta "{goal.name}" criada!')
            return redirect('budget_list')
    else:
        form = GoalForm(family_group=group)

    budgets = Budget.objects.filter(family_group=group, reference_month=date.today().replace(day=1)).select_related(
        'category'
    )
    goals = FinancialGoal.objects.filter(family_group=group, is_completed=False).select_related('linked_account')
    return render(
        request,
        'budgets/list.html',
        {
            'goal_form': form,
            'show_goal_modal': True,
            'budgets': budgets,
            'goals': goals,
            'ref_month': date.today().replace(day=1),
        },
    )


@login_required
@family_edit_required
def goal_contribute(request, pk):
    group = request.user.profile.family_group
    goal = get_object_or_404(FinancialGoal, pk=pk, family_group=group)

    if request.method == 'POST':
        form = ContributionForm(request.POST, family_group=group)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            contribution_date = form.cleaned_data['date']
            notes = form.cleaned_data.get('notes', '')
            account = form.cleaned_data.get('account')

            with transaction.atomic():
                contribution_transaction = None
                if account:
                    tx_data = {
                        'user': request.user,
                        'family_group': group,
                        'account': account,
                        'category': _get_transfer_category(),
                        'description': f'Aporte para meta {goal.name}',
                        'amount': amount,
                        'date': contribution_date,
                        'status': 'paid',
                        'notes': notes,
                    }
                    if goal.linked_account and goal.linked_account != account:
                        tx_data['transaction_type'] = 'transfer'
                        tx_data['destination_account'] = goal.linked_account
                    else:
                        tx_data['transaction_type'] = 'expense'

                    contribution_transaction = Transaction.objects.create(**tx_data)

                GoalContribution.objects.create(
                    goal=goal,
                    amount=amount,
                    date=contribution_date,
                    notes=notes,
                    transaction=contribution_transaction,
                )
                goal.current_amount += amount
                if goal.current_amount >= goal.target_amount:
                    goal.is_completed = True
                    messages.success(request, f'Parab\u00e9ns! Meta "{goal.name}" atingida!')
                goal.save()

            if not goal.is_completed:
                messages.success(request, f'Aporte de R$ {amount} registrado!')
    return redirect('budget_list')
