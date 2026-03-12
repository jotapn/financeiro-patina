from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from apps.transactions.models import Transaction


@login_required
def reports_home(request):
    group = request.user.profile.family_group
    today = date.today()
    view_mode = request.GET.get('view', 'personal')

    if view_mode == 'family':
        qs = Transaction.objects.filter(family_group=group, status='paid', is_ignored=False)
    else:
        qs = Transaction.objects.filter(user=request.user, status='paid', is_ignored=False)

    flow_data = []
    for i in range(11, -1, -1):
        ref = today.replace(day=1) - relativedelta(months=i)
        income = (
            qs.filter(date__year=ref.year, date__month=ref.month, transaction_type='income').aggregate(t=Sum('amount'))['t']
            or 0
        )
        expense = (
            qs.filter(date__year=ref.year, date__month=ref.month, transaction_type='expense').aggregate(t=Sum('amount'))['t']
            or 0
        )
        flow_data.append(
            {
                'month': ref.strftime('%b/%y'),
                'income': float(income),
                'expense': float(expense),
                'balance': float(income) - float(expense),
            }
        )

    year_expenses_raw = (
        qs.filter(date__year=today.year, transaction_type='expense')
        .values('category__name', 'category__color')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:10]
    )

    year_income = qs.filter(date__year=today.year, transaction_type='income').aggregate(t=Sum('amount'))['t'] or 0
    year_expense = qs.filter(date__year=today.year, transaction_type='expense').aggregate(t=Sum('amount'))['t'] or 0

    month_by_category_raw = (
        qs.filter(date__year=today.year, date__month=today.month, transaction_type='expense')
        .values('category__name', 'category__color', 'category__icon')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    year_expenses = [
        {**item, 'total': float(item['total'] or 0)}
        for item in year_expenses_raw
    ]
    month_by_category = [
        {**item, 'total': float(item['total'] or 0)}
        for item in month_by_category_raw
    ]

    context = {
        'flow_data': flow_data,
        'year_expenses': year_expenses,
        'year_income': year_income,
        'year_expense': year_expense,
        'year_savings': float(year_income) - float(year_expense),
        'month_by_category': month_by_category,
        'view_mode': view_mode,
        'today': today,
    }
    return render(request, 'reports/home.html', context)
