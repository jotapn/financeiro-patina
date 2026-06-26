from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import family_edit_required
from apps.core.security import rate_limit_post

from .forms import FinancialAccountForm, TransferForm
from .models import FinancialAccount


@login_required
def account_list(request):
    group = request.user.profile.family_group
    accounts = list(
        FinancialAccount.objects.filter(family_group=group, is_active=True)
        .select_related('owner')
        .with_current_balance()
    )
    total_balance = sum(a.current_balance for a in accounts if a.include_in_total)
    return render(
        request,
        'accounts/list.html',
        {
            'accounts': accounts,
            'total_balance': total_balance,
        },
    )


@login_required
@family_edit_required
@rate_limit_post('account_create')
def account_create(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = FinancialAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.owner = request.user
            account.family_group = group
            account.save()
            messages.success(request, 'Conta criada com sucesso!')
            return redirect('account_list')
    else:
        form = FinancialAccountForm()

    return render(
        request,
        'accounts/form.html',
        {
            'form': form,
            'editing': None,
        },
    )


@login_required
def account_detail(request, pk):
    group = request.user.profile.family_group
    account = get_object_or_404(FinancialAccount.objects.with_current_balance(), pk=pk, family_group=group)
    transactions = account.transactions.select_related('category', 'user').order_by('-date')[:20]
    return render(request, 'accounts/detail.html', {'account': account, 'transactions': transactions})


@login_required
@family_edit_required
@rate_limit_post('account_edit')
def account_edit(request, pk):
    group = request.user.profile.family_group
    account = get_object_or_404(FinancialAccount, pk=pk, family_group=group)
    if request.method == 'POST':
        form = FinancialAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada!')
            return redirect('account_list')
    else:
        form = FinancialAccountForm(instance=account)

    return render(
        request,
        'accounts/form.html',
        {
            'form': form,
            'editing': account,
        },
    )


@login_required
@family_edit_required
@rate_limit_post('account_delete')
def account_delete(request, pk):
    group = request.user.profile.family_group
    account = get_object_or_404(FinancialAccount, pk=pk, family_group=group)
    if request.method == 'POST':
        account.is_active = False
        account.save()
        messages.success(request, 'Conta removida.')
    return redirect('account_list')


@login_required
@family_edit_required
@rate_limit_post('account_transfer')
def transfer(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = TransferForm(request.POST, family_group=group)
        if form.is_valid():
            from apps.categories.models import Category
            from apps.transactions.models import Transaction

            transfer_cat = Category.objects.filter(name='Transfer\u00eancia', is_system=True).first() or Category.objects.filter(
                is_system=True
            ).first()
            data = form.cleaned_data
            Transaction.objects.create(
                user=request.user,
                family_group=group,
                account=data['from_account'],
                destination_account=data['to_account'],
                category=transfer_cat,
                description=data.get('description', 'Transfer\u00eancia'),
                amount=data['amount'],
                transaction_type='transfer',
                date=data['date'],
                status='paid',
            )
            messages.success(request, 'Transfer\u00eancia realizada!')
            return redirect('account_list')
    else:
        form = TransferForm(family_group=group)

    return render(
        request,
        'accounts/transfer.html',
        {
            'transfer_form': form,
        },
    )
