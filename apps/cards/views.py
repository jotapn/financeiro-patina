from calendar import monthrange
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.categories.models import Category
from apps.transactions.forms import TransactionForm
from apps.transactions.models import Transaction

from .forms import CreditCardForm, InvoicePaymentForm
from .models import CardInvoice, CreditCard


def _safe_replace_day(any_date, day):
    return any_date.replace(day=min(day, monthrange(any_date.year, any_date.month)[1]))


def _get_invoice_for_date(card, tx_date):
    if tx_date.day <= card.closing_day:
        ref = tx_date.replace(day=1)
    else:
        ref = tx_date.replace(day=1) + relativedelta(months=1)

    closing_date = _safe_replace_day(ref, card.closing_day)
    due_base = ref + relativedelta(months=1)
    due_date = _safe_replace_day(due_base, card.due_day)

    invoice, _ = CardInvoice.objects.get_or_create(
        card=card,
        reference_month=ref,
        defaults={
            'closing_date': closing_date,
            'due_date': due_date,
            'status': 'open',
        },
    )
    return invoice


def _update_invoice_total(invoice):
    total = invoice.transactions.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    invoice.total_amount = total
    invoice.save(update_fields=['total_amount'])


def _create_installments(parent_tx, card, total):
    installment_amount = (parent_tx.amount / total).quantize(Decimal('0.01'))
    parent_tx.installment_number = 1
    parent_tx.installment_total = total
    parent_tx.amount = installment_amount
    parent_tx.save()

    base_date = parent_tx.date
    for i in range(2, total + 1):
        future_date = base_date + relativedelta(months=i - 1)
        future_invoice = _get_invoice_for_date(card, future_date)
        Transaction.objects.create(
            user=parent_tx.user,
            family_group=parent_tx.family_group,
            credit_card=card,
            invoice=future_invoice,
            category=parent_tx.category,
            description=f'{parent_tx.description} ({i}/{total})',
            amount=installment_amount,
            transaction_type='expense',
            date=future_date,
            status='scheduled',
            parent_transaction=parent_tx,
            installment_number=i,
            installment_total=total,
        )
        _update_invoice_total(future_invoice)


def _generate_future_invoices(card, months=3):
    today = date.today()
    ref = today.replace(day=1)
    for i in range(months):
        month_ref = ref + relativedelta(months=i)
        closing = _safe_replace_day(month_ref, card.closing_day)
        due = _safe_replace_day(month_ref + relativedelta(months=1), card.due_day)
        status = 'open' if i == 0 else 'future'
        CardInvoice.objects.get_or_create(
            card=card,
            reference_month=month_ref,
            defaults={'closing_date': closing, 'due_date': due, 'status': status},
        )


@login_required
def card_list(request):
    group = request.user.profile.family_group
    cards = CreditCard.objects.filter(family_group=group, is_active=True).prefetch_related('invoices')

    cards_data = []
    for card in cards:
        current_inv = card.invoices.filter(status='open').order_by('reference_month').first()
        next_inv = card.invoices.filter(status='future').order_by('reference_month').first()
        cards_data.append(
            {
                'card': card,
                'current_invoice': current_inv,
                'next_invoice': next_inv,
            }
        )

    return render(request, 'cards/list.html', {'cards_data': cards_data})


@login_required
def card_create(request):
    group = request.user.profile.family_group
    if request.method == 'POST':
        form = CreditCardForm(request.POST, family_group=group)
        if form.is_valid():
            card = form.save(commit=False)
            card.owner = request.user
            card.family_group = group
            card.save()
            _generate_future_invoices(card, 3)
            messages.success(request, f'Cartão {card.name} cadastrado!')
            return redirect('card_list')
    else:
        form = CreditCardForm(family_group=group)

    cards = CreditCard.objects.filter(family_group=group, is_active=True).prefetch_related('invoices')
    cards_data = []
    for card in cards:
        cards_data.append(
            {
                'card': card,
                'current_invoice': card.invoices.filter(status='open').order_by('reference_month').first(),
                'next_invoice': card.invoices.filter(status='future').order_by('reference_month').first(),
            }
        )
    return render(request, 'cards/list.html', {'form': form, 'show_modal': True, 'cards_data': cards_data})


@login_required
def card_detail(request, pk):
    group = request.user.profile.family_group
    card = get_object_or_404(CreditCard, pk=pk, family_group=group)
    expense_categories = Category.objects.filter(
        Q(family_group=group) | Q(is_system=True), category_type='expense'
    ).order_by('name')
    invoices = card.invoices.order_by('-reference_month')[:12]

    invoice_pk = request.GET.get('invoice')
    if invoice_pk:
        selected_invoice = get_object_or_404(CardInvoice, pk=invoice_pk, card=card)
    else:
        selected_invoice = card.invoices.filter(status='open').order_by('reference_month').first()

    invoice_transactions = []
    if selected_invoice:
        invoice_transactions = selected_invoice.transactions.select_related('category', 'user').order_by('-date')

    return render(
        request,
        'cards/detail.html',
        {
            'card': card,
            'expense_categories': expense_categories,
            'invoices': invoices,
            'selected_invoice': selected_invoice,
            'invoice_transactions': invoice_transactions,
        },
    )


@login_required
def pay_invoice(request, pk):
    group = request.user.profile.family_group
    invoice = get_object_or_404(CardInvoice, pk=pk, card__family_group=group)

    if request.method == 'POST':
        form = InvoicePaymentForm(request.POST, invoice=invoice)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            account = form.cleaned_data['account']
            payment_date = form.cleaned_data['payment_date']

            pay_cat = Category.objects.filter(name='Moradia', is_system=True).first() or Category.objects.filter(
                is_system=True
            ).first()

            tx = Transaction.objects.create(
                user=request.user,
                family_group=group,
                account=account,
                category=pay_cat,
                description=f'Pagamento fatura {invoice.card.name} {invoice.reference_month.strftime("%m/%Y")}',
                amount=amount,
                transaction_type='expense',
                date=payment_date,
                status='paid',
            )
            invoice.paid_amount += amount
            invoice.payment_transaction = tx
            invoice.status = 'paid' if invoice.paid_amount >= invoice.total_amount else 'partial'
            invoice.payment_date = payment_date
            invoice.save()
            messages.success(request, f'Pagamento de R$ {amount} registrado!')
            return redirect('card_detail', pk=invoice.card.pk)
    else:
        form = InvoicePaymentForm(invoice=invoice)

    return render(request, 'cards/pay_invoice.html', {'invoice': invoice, 'form': form})


@login_required
def add_card_transaction(request, card_pk):
    group = request.user.profile.family_group
    card = get_object_or_404(CreditCard, pk=card_pk, family_group=group)

    if request.method == 'POST':
        form = TransactionForm(request.POST, family_group=group)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.user = request.user
            tx.family_group = group
            tx.credit_card = card
            tx.transaction_type = 'expense'

            invoice = _get_invoice_for_date(card, tx.date)
            tx.invoice = invoice
            tx.save()

            installments = form.cleaned_data.get('installment_total', 1) or 1
            if installments > 1:
                _create_installments(tx, card, installments)

            _update_invoice_total(invoice)
            messages.success(request, 'Lançamento no cartão adicionado!')
        else:
            messages.error(request, 'Não foi possível salvar lançamento no cartão.')

    return redirect('card_detail', pk=card_pk)
