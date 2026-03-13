import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from langchain.tools import tool

from apps.accounts.models import FinancialAccount
from apps.budgets.models import Budget, FinancialGoal
from apps.cards.models import CardInvoice, CreditCard
from apps.investments.models import Investment, InvestmentGoal, InvestmentTransaction
from apps.transactions.models import Transaction


def _month_range(month: int, year: int):
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    return start, end


def build_tools_for_user(user):
    group = user.profile.family_group

    @tool
    def get_monthly_summary(month: int, year: int) -> dict:
        """Retorna resumo do mês: total receitas, despesas, saldo, número de transações e comparativo com mês anterior."""
        start, end = _month_range(month, year)
        qs = Transaction.objects.filter(user=user, date__range=(start, end), is_ignored=False)
        income = qs.filter(transaction_type='income', status='paid').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        expense = qs.filter(transaction_type='expense', status='paid').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        prev_month = start - timedelta(days=1)
        prev_expense = Transaction.objects.filter(
            user=user,
            date__year=prev_month.year,
            date__month=prev_month.month,
            transaction_type='expense',
            status='paid',
            is_ignored=False,
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        return {
            'month': f'{month:02d}/{year}',
            'income': float(income),
            'expense': float(expense),
            'balance': float(income - expense),
            'transactions_count': qs.count(),
            'expense_vs_previous_month': float(expense - prev_expense),
        }

    @tool
    def get_expenses_by_category(month: int, year: int, scope: str = 'personal') -> list:
        """Retorna gastos por categoria com percentual do total. scope: personal ou family."""
        start, end = _month_range(month, year)
        qs = Transaction.objects.filter(date__range=(start, end), transaction_type='expense', status='paid', is_ignored=False)
        qs = qs.filter(family_group=group) if scope == 'family' and group else qs.filter(user=user)
        rows = list(qs.values('category__name').annotate(total=Sum('amount')).order_by('-total'))
        total = sum((row['total'] or Decimal('0')) for row in rows) or Decimal('1')
        return [
            {
                'category': row['category__name'],
                'total': float(row['total'] or 0),
                'percentage': round(float((row['total'] or 0) / total * 100), 1),
            }
            for row in rows
        ]

    @tool
    def get_account_balances(include_investments: bool = False) -> list:
        """Saldo atual de todas as contas ativas. Se include_investments=True, inclui valor da carteira."""
        accounts = FinancialAccount.objects.filter(owner=user, is_active=True)
        data = [
            {'name': account.name, 'balance': float(account.current_balance), 'type': account.get_account_type_display()}
            for account in accounts
        ]
        if include_investments:
            portfolio_total = sum(inv.current_value for inv in Investment.objects.filter(owner=user, is_active=True))
            data.append({'name': 'Carteira de investimentos', 'balance': float(portfolio_total), 'type': 'Investimentos'})
        return data

    @tool
    def get_budget_status(month: int, year: int) -> list:
        """Status de todos os orçamentos: limite, gasto, % usado."""
        budgets = Budget.objects.filter(owner=user, reference_month=date(year, month, 1)).select_related('category')
        return [
            {
                'category': budget.category.name if budget.category else 'Sem categoria',
                'limit': float(budget.amount),
                'spent': float(budget.spent_amount),
                'used_pct': budget.percentage_used,
                'is_over_budget': budget.is_over_budget,
            }
            for budget in budgets
        ]

    @tool
    def get_top_expenses(limit: int = 10, period: str = 'current_month') -> list:
        """Maiores despesas do período. period: current_month | last_month | last_30_days | current_year"""
        qs = Transaction.objects.filter(user=user, transaction_type='expense', is_ignored=False)
        today = date.today()
        if period == 'current_month':
            qs = qs.filter(date__year=today.year, date__month=today.month)
        elif period == 'last_month':
            prev = today.replace(day=1) - timedelta(days=1)
            qs = qs.filter(date__year=prev.year, date__month=prev.month)
        elif period == 'last_30_days':
            qs = qs.filter(date__gte=today - timedelta(days=30))
        elif period == 'current_year':
            qs = qs.filter(date__year=today.year)
        return [{'description': tx.description, 'amount': float(tx.amount), 'date': tx.date.isoformat(), 'category': tx.category.name} for tx in qs.order_by('-amount')[:limit]]

    @tool
    def get_investment_portfolio(scope: str = 'personal') -> dict:
        """Carteira: valor total, rentabilidade, alocação, proventos do mês."""
        investments = Investment.objects.filter(is_active=True)
        investments = investments.filter(family_group=group) if scope == 'family' and group else investments.filter(owner=user)
        total_current = sum(inv.current_value for inv in investments)
        total_invested = sum(inv.total_invested for inv in investments)
        month_dividends = InvestmentTransaction.objects.filter(
            investment__in=investments,
            transaction_type__in=('dividend', 'jcp', 'income'),
            date__year=date.today().year,
            date__month=date.today().month,
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        allocation = defaultdict(Decimal)
        for inv in investments.select_related('asset_class'):
            key = inv.asset_class.name if inv.asset_class else 'Sem classe'
            allocation[key] += inv.current_value
        return {
            'total_current': float(total_current),
            'total_invested': float(total_invested),
            'profit_loss': float(total_current - total_invested),
            'allocation': {key: float(value) for key, value in allocation.items()},
            'monthly_dividends': float(month_dividends),
        }

    @tool
    def get_upcoming_bills(days_ahead: int = 30) -> list:
        """Faturas de cartão e lançamentos agendados nos próximos N dias."""
        due_limit = date.today() + timedelta(days=days_ahead)
        invoices = CardInvoice.objects.filter(card__owner=user, due_date__lte=due_limit).select_related('card')
        scheduled = Transaction.objects.filter(user=user, status='scheduled', date__lte=due_limit)
        data = [
            {'type': 'invoice', 'title': f'Fatura {invoice.card.name}', 'amount': float(invoice.total_amount), 'due_date': invoice.due_date.isoformat()}
            for invoice in invoices
        ]
        data.extend([
            {'type': 'transaction', 'title': tx.description, 'amount': float(tx.amount), 'due_date': tx.date.isoformat()}
            for tx in scheduled
        ])
        return sorted(data, key=lambda item: item['due_date'])

    @tool
    def get_cash_flow_trend(months: int = 6) -> list:
        """Fluxo de caixa dos últimos N meses: receitas, despesas, saldo."""
        today = date.today()
        trend = []
        for offset in range(months - 1, -1, -1):
            ref = today.replace(day=1) - timedelta(days=offset * 30)
            month_qs = Transaction.objects.filter(user=user, date__year=ref.year, date__month=ref.month, status='paid', is_ignored=False)
            income = month_qs.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or Decimal('0')
            expense = month_qs.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or Decimal('0')
            trend.append({'month': ref.strftime('%m/%Y'), 'income': float(income), 'expense': float(expense), 'balance': float(income - expense)})
        return trend

    @tool
    def get_savings_rate(month: int, year: int) -> dict:
        """Taxa de poupança: (receita-despesa)/receita*100. Compara com benchmark de 20% e com histórico."""
        start, end = _month_range(month, year)
        qs = Transaction.objects.filter(user=user, date__range=(start, end), status='paid', is_ignored=False)
        income = qs.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        expense = qs.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        rate = ((income - expense) / income * 100) if income else Decimal('0')
        return {'rate': round(float(rate), 2), 'benchmark': 20.0}

    @tool
    def get_spending_anomalies(month: int, year: int) -> list:
        """Categorias com gasto > 30% acima da média dos últimos 3 meses."""
        start, end = _month_range(month, year)
        current = Transaction.objects.filter(user=user, date__range=(start, end), transaction_type='expense', status='paid', is_ignored=False).values('category__name').annotate(total=Sum('amount'))
        anomalies = []
        for row in current:
            history = []
            ref_cursor = start
            for _ in range(3):
                ref_end = ref_cursor - timedelta(days=1)
                ref = date(ref_end.year, ref_end.month, 1)
                total = Transaction.objects.filter(user=user, date__year=ref.year, date__month=ref.month, transaction_type='expense', status='paid', is_ignored=False, category__name=row['category__name']).aggregate(t=Sum('amount'))['t'] or Decimal('0')
                history.append(total)
                ref_cursor = ref
            avg_history = sum(history) / len(history) if history else Decimal('0')
            if avg_history > 0 and row['total'] > avg_history * Decimal('1.3'):
                anomalies.append({'category': row['category__name'], 'current': float(row['total']), 'average_3_months': float(avg_history)})
        return anomalies

    @tool
    def get_card_info() -> list:
        """Todos os cartões: limite, disponível, fatura aberta, vencimento."""
        cards = CreditCard.objects.filter(owner=user, is_active=True).prefetch_related('invoices')
        return [
            {
                'name': card.name,
                'limit': float(card.credit_limit),
                'available': float(card.available_limit),
                'current_invoice': float(card.current_invoice.total_amount) if card.current_invoice else 0,
                'due_date': card.current_invoice.due_date.isoformat() if card.current_invoice else '',
            }
            for card in cards
        ]

    @tool
    def get_financial_goals_status() -> list:
        """Metas ativas: progresso, valor atual, prazo restante."""
        goals = list(FinancialGoal.objects.filter(owner=user, is_completed=False))
        goals.extend(list(InvestmentGoal.objects.filter(owner=user, is_completed=False)))
        data = []
        for goal in goals:
            current_amount = getattr(goal, 'current_amount', 0)
            target_amount = getattr(goal, 'target_amount', 0) or 0
            pct = round(float(current_amount / target_amount * 100), 1) if target_amount else 0
            data.append({'name': goal.name, 'current_amount': float(current_amount), 'target_amount': float(target_amount), 'progress_pct': min(pct, 100), 'target_date': goal.target_date.isoformat() if goal.target_date else ''})
        return data

    return [get_monthly_summary, get_expenses_by_category, get_account_balances, get_budget_status, get_top_expenses, get_investment_portfolio, get_upcoming_bills, get_cash_flow_trend, get_savings_rate, get_spending_anomalies, get_card_info, get_financial_goals_status]
