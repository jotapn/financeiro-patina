from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.categories.models import Category
from apps.notifications.models import Notification

from .forms import TransactionForm
from .importers import CSVImporter
from .models import RecurrenceRule, Transaction
from .ocr import extract_receipt_data


def _upsert_recurrence_rule(form, tx):
    frequency = form.cleaned_data.get('recurrence_frequency')
    if not frequency:
        return None
    recurrence_rule = tx.recurrence_rule or RecurrenceRule()
    recurrence_rule.frequency = frequency
    recurrence_rule.interval = form.cleaned_data.get('recurrence_interval') or 1
    recurrence_rule.end_date = form.cleaned_data.get('recurrence_end_date')
    recurrence_rule.max_occurrences = form.cleaned_data.get('recurrence_max_occurrences')
    recurrence_rule.save()
    return recurrence_rule


@login_required
def transaction_list(request):
    group = request.user.profile.family_group
    qs = Transaction.objects.filter(family_group=group).select_related('category', 'account', 'credit_card', 'user')

    tx_type = request.GET.get('type')
    period = request.GET.get('period', 'current_month')
    category_id = request.GET.get('category')
    search = request.GET.get('q')

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
        qs = qs.filter(Q(description__icontains=search) | Q(notes__icontains=search) | Q(location__icontains=search))

    totals = qs.filter(status='paid').aggregate(income=Sum('amount', filter=Q(transaction_type='income')), expense=Sum('amount', filter=Q(transaction_type='expense')))
    categories = Category.objects.filter(Q(family_group=group) | Q(is_system=True)).order_by('name')

    return render(request, 'transactions/list.html', {'transactions': qs.order_by('-date', '-created_at'), 'totals': totals, 'categories': categories, 'filters': {'type': tx_type, 'period': period, 'category': category_id, 'q': search}, 'form': TransactionForm(family_group=group)})


@login_required
def transaction_create(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES, family_group=group)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.user = request.user
            tx.family_group = group
            tx.recurrence_rule = _upsert_recurrence_rule(form, tx)
            tx.save()
            form.save_m2m()
            if request.htmx:
                return render(request, 'transactions/partials/transaction_row.html', {'tx': tx})
            messages.success(request, 'Transação criada!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(family_group=group)
    return render(request, 'transactions/list.html', {'form': form, 'show_modal': True})


@login_required
def transaction_edit(request, pk):
    group = request.user.profile.family_group
    tx = get_object_or_404(Transaction, pk=pk, family_group=group)
    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES, instance=tx, family_group=group)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.recurrence_rule = _upsert_recurrence_rule(form, tx)
            tx.save()
            form.save_m2m()
            messages.success(request, 'Transação atualizada!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=tx, family_group=group)
    return render(request, 'transactions/list.html', {'form': form, 'show_modal': True, 'editing': tx})


@login_required
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
def toggle_status(request, pk):
    group = request.user.profile.family_group
    tx = get_object_or_404(Transaction, pk=pk, family_group=group)
    if request.method == 'POST':
        tx.status = 'paid' if tx.status != 'paid' else 'pending'
        tx.save()
        if request.htmx:
            return render(request, 'transactions/partials/transaction_row.html', {'tx': tx})
    return redirect('transaction_list')


@login_required
def import_csv(request):
    group = request.user.profile.family_group
    importer = CSVImporter()

    if request.method == 'POST':
        uploaded = request.FILES.get('csv_file')
        bank_type = request.POST.get('bank_type')
        confirm = request.POST.get('confirm') == '1'

        if not uploaded and not confirm:
            messages.error(request, 'Selecione um arquivo CSV.')
            return redirect('import-csv')

        if uploaded:
            if not bank_type:
                bank_type = importer.detect_bank(uploaded)
            rows = importer.parse(uploaded, bank_type)
            importer.detect_duplicates(rows, request.user)
            cache_key = f'csv_import_preview_{request.user.pk}'
            cache.set(cache_key, rows, 900)
        else:
            rows = cache.get(f'csv_import_preview_{request.user.pk}', [])
            bank_type = request.POST.get('bank_type', 'generic')

        if confirm:
            category = Category.objects.filter(Q(family_group=group) | Q(is_system=True), category_type='expense').first()
            imported = duplicates = errors = 0
            for row in rows:
                if row.get('is_duplicate'):
                    duplicates += 1
                    continue
                try:
                    Transaction.objects.create(user=request.user, family_group=group, category=category, description=row['description'], amount=row['amount'], transaction_type=row['transaction_type'], date=row['date'], status='paid')
                    imported += 1
                except Exception:
                    errors += 1
            messages.success(request, f'Importação concluída: {imported} importadas, {duplicates} duplicatas ignoradas, {errors} com erro.')
            return redirect('transaction_list')

        return render(request, 'transactions/import.html', {'detected_bank': bank_type, 'preview_rows': rows[:10], 'all_rows_count': len(rows), 'duplicates_count': sum(1 for row in rows if row.get('is_duplicate'))})

    return render(request, 'transactions/import.html')


@login_required
def ocr_receipt(request):
    if request.method != 'POST' or 'receipt' not in request.FILES:
        return JsonResponse({'error': 'Arquivo inválido.'}, status=400)

    uploaded = request.FILES['receipt']
    from django.core.files.storage import default_storage

    temp_path = default_storage.save(f'tmp/{uploaded.name}', uploaded)
    absolute_path = default_storage.path(temp_path)
    payload = extract_receipt_data(absolute_path)
    default_storage.delete(temp_path)
    return JsonResponse(payload)


@login_required
def confirm_scheduled(request, id):
    group = request.user.profile.family_group
    tx = get_object_or_404(Transaction, pk=id, family_group=group, user=request.user)
    if request.method == 'POST':
        tx.status = 'paid'
        tx.save(update_fields=['status'])
        Notification.objects.filter(user=request.user, action_url=f'/transactions/{tx.pk}/confirm/').update(is_read=True)
        messages.success(request, 'Transação agendada confirmada.')
    return redirect('transaction_list')
