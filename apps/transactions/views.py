from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.categories.models import Category
from apps.core.decorators import family_edit_required
from apps.core.security import rate_limit_post

from .forms import TransactionForm
from .models import Transaction


def _build_transaction_list_context(group, *, filters=None):
    qs = Transaction.objects.filter(family_group=group).select_related(
        'category', 'account', 'credit_card', 'user'
    )

    filters = filters or {}
    tx_type = filters.get('type')
    period = filters.get('period', 'current_month')
    category_id = filters.get('category')
    search = filters.get('q')

    today = date.today()
    if period == 'current_month':
        qs = qs.filter(date__year=today.year, date__month=today.month)
    elif period == 'last_month':
        last_month = today.replace(day=1) - timedelta(days=1)
        qs = qs.filter(date__year=last_month.year, date__month=last_month.month)
    elif period == 'current_year':
        qs = qs.filter(date__year=today.year)

    if tx_type in ('income', 'expense', 'transfer'):
        qs = qs.filter(transaction_type=tx_type)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if search:
        qs = qs.filter(
            Q(description__icontains=search)
            | Q(notes__icontains=search)
            | Q(location__icontains=search)
        )

    totals = qs.filter(status='paid').aggregate(
        income=Sum('amount', filter=Q(transaction_type='income')),
        expense=Sum('amount', filter=Q(transaction_type='expense')),
    )
    categories = Category.objects.filter(Q(family_group=group) | Q(is_system=True)).order_by('name')

    return {
        'transactions': qs.order_by('-date', '-created_at'),
        'totals': totals,
        'categories': categories,
        'filters': {
            'type': tx_type,
            'period': period,
            'category': category_id,
            'q': search,
        },
    }


@login_required
def transaction_list(request):
    group = request.user.profile.family_group
    context = _build_transaction_list_context(
        group,
        filters={
            'type': request.GET.get('type'),
            'period': request.GET.get('period', 'current_month'),
            'category': request.GET.get('category'),
            'q': request.GET.get('q'),
        },
    )
    return render(request, 'transactions/list.html', context)


@login_required
@family_edit_required
@rate_limit_post('transaction_create')
def transaction_create(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES, family_group=group)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.user = request.user
            tx.family_group = group
            tx.save()
            form.save_m2m()
            if request.htmx:
                return render(request, 'transactions/partials/transaction_row.html', {'tx': tx})
            messages.success(request, 'Transação criada!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(family_group=group)

    return render(request, 'transactions/form.html', {'form': form, 'editing': None})


@login_required
@family_edit_required
@rate_limit_post('transaction_edit')
def transaction_edit(request, pk):
    group = request.user.profile.family_group
    tx = get_object_or_404(Transaction, pk=pk, family_group=group)
    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES, instance=tx, family_group=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transação atualizada!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=tx, family_group=group)

    return render(request, 'transactions/form.html', {'form': form, 'editing': tx})


@login_required
@family_edit_required
@rate_limit_post('transaction_delete')
def transaction_delete(request, pk):
    group = request.user.profile.family_group
    tx = get_object_or_404(Transaction, pk=pk, family_group=group)
    if request.method == 'POST':
        tx.delete()
        if request.htmx:
            return render(request, 'transactions/partials/empty_row.html')
        messages.success(request, 'Transação excluída.')
    return redirect('transaction_list')


@login_required
@family_edit_required
@rate_limit_post('transaction_toggle_status')
def toggle_status(request, pk):
    group = request.user.profile.family_group
    tx = get_object_or_404(Transaction, pk=pk, family_group=group)
    if request.method == 'POST':
        tx.status = 'paid' if tx.status != 'paid' else 'pending'
        tx.save()
        if request.htmx:
            return render(request, 'transactions/partials/transaction_row.html', {'tx': tx})
    return redirect('transaction_list')
