from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BudgetForm, ContributionForm, GoalForm
from .models import Budget, FinancialGoal, GoalContribution


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
def budget_create(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = BudgetForm(request.POST, family_group=group)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.owner = request.user
            budget.family_group = group
            budget.save()
            messages.success(request, 'Orçamento criado!')
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

    messages.success(request, f'{created} orçamento(s) copiado(s) do mês anterior!')
    return redirect('budget_list')


@login_required
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
def goal_contribute(request, pk):
    group = request.user.profile.family_group
    goal = get_object_or_404(FinancialGoal, pk=pk, family_group=group)

    if request.method == 'POST':
        form = ContributionForm(request.POST, family_group=group)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            GoalContribution.objects.create(
                goal=goal,
                amount=amount,
                date=form.cleaned_data['date'],
                notes=form.cleaned_data.get('notes', ''),
            )
            goal.current_amount += amount
            if goal.current_amount >= goal.target_amount:
                goal.is_completed = True
                messages.success(request, f'Parabéns! Meta "{goal.name}" atingida!')
            goal.save()
            if not goal.is_completed:
                messages.success(request, f'Aporte de R$ {amount} registrado!')
    return redirect('budget_list')
