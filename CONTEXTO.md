# CONTEXTO - FinanceFlow (Fase 2)

## 1) Models criados/atualizados (campos principais)

### apps.core
- `User`: `email` (único), `username`, `first_name`, `last_name`, `is_active`.
- `FamilyGroup`: `name`, `invite_code`, `created_at`.
- `UserProfile`: `user`, `family_group`, `role`, `avatar`, `default_currency`, `timezone`, `financial_month_start_day`, `monthly_income`, preferências de notificação.
- `FamilyInvitation`: `family_group`, `email`, `token`, `invited_by`, `accepted`, `created_at`, `expires_at`.

### apps.accounts
- `FinancialAccount`: `owner`, `family_group`, `ownership`, `name`, `account_type`, `bank`, `initial_balance`, `color`, `include_in_total`, `is_active`.
- `PaymentMethod`: `family_group`, `name`, `method_type`, `is_default`, `is_active`.

### apps.transactions
- `Tag`, `RecurrenceRule`, `Transaction` (com suporte a `credit_card`, `invoice`, `installment_number`, `installment_total`, `parent_transaction`).

### apps.cards
- `CreditCard`: dados do cartão, limite, fechamento/vencimento, conta de débito, cores e ownership.
- `CardInvoice`: `card`, `reference_month`, `closing_date`, `due_date`, `total_amount`, `paid_amount`, `status`, `payment_date`, **`payment_transaction`**.

### apps.categories
- `Category`, `Subcategory`.

### apps.budgets
- `Budget`: `family_group`, `owner`, `category`, `amount`, `period`, `scope`, `reference_month`, `rollover`, `alert_threshold` (com propriedades de consumo/progresso).
- `FinancialGoal`: tipo/escopo da meta, valor alvo/atual, data alvo, conta vinculada, aporte mensal, progresso.
- `GoalContribution`: `goal`, `amount`, `date`, `notes`, `transaction`.

### apps.investments
- `Investment`: `family_group`, `name`, `amount`, `created_at`.

### apps.ai_assistant
- `AiAssistantLog`.

### apps.notifications
- `Notification`.

---

## 2) URLs disponíveis

### config/urls.py
- `/admin/`
- `/` + `apps.core.urls`
- `/auth/` + `django.contrib.auth.urls`
- `/accounts/` + `apps.accounts.urls`
- `/transactions/` + `apps.transactions.urls`
- `/cards/` + `apps.cards.urls`
- `/categories/` + `apps.categories.urls`
- `/budgets/` + `apps.budgets.urls`
- `/reports/` + `apps.reports.urls`

### apps.core.urls
- `/` (`dashboard`)
- `/auth/register/` (`register`)
- `/auth/login/` (`login`)
- `/auth/logout/` (`logout`)
- `/profile/` (`profile`)
- `/family/` (`family`)
- `/family/invite/` (`invite_member`)
- `/family/accept/<uuid:token>/` (`accept_invite`)

### apps.accounts.urls
- `/accounts/`
- `/accounts/create/`
- `/accounts/<int:pk>/`
- `/accounts/<int:pk>/edit/`
- `/accounts/<int:pk>/delete/`
- `/accounts/transfer/`

### apps.transactions.urls
- `/transactions/`
- `/transactions/create/`
- `/transactions/<int:pk>/edit/`
- `/transactions/<int:pk>/delete/`
- `/transactions/<int:pk>/toggle-status/`

### apps.cards.urls
- `/cards/` (`card_list`)
- `/cards/create/` (`card_create`)
- `/cards/<int:pk>/` (`card_detail`)
- `/cards/<int:pk>/pay/` (`pay_invoice`)
- `/cards/<int:card_pk>/add-transaction/` (`add_card_transaction`)

### apps.categories.urls
- `/categories/` (`category_list`)
- `/categories/ensure-transfer/` (`ensure_transfer_category`)

### apps.budgets.urls
- `/budgets/` (`budget_list`)
- `/budgets/create/` (`budget_create`)
- `/budgets/clone/` (`budget_clone`)
- `/budgets/goals/create/` (`goal_create`)
- `/budgets/goals/<int:pk>/contribute/` (`goal_contribute`)

### apps.reports.urls
- `/reports/` (`reports_home`)

---

## 3) Decisões técnicas importantes

- `DATABASE_URL` ganhou prioridade no settings para suportar Supabase diretamente, com SSL.
- Cards Fase 2:
  - geração automática de faturas futuras;
  - pagamento parcial/total com vínculo da transação de pagamento em `CardInvoice.payment_transaction`;
  - distribuição de parcelamento em faturas futuras.
- Orçamentos e metas:
  - cálculo de gasto por categoria no mês;
  - progresso (%), saldo restante e alerta visual;
  - clonagem do mês anterior e aportes em metas.
- Relatórios:
  - fluxo de 12 meses (receita/despesa);
  - top categorias do ano;
  - pizza mensal por categoria.
- Sidebar atualizada com links reais de Cartões, Orçamentos e Relatórios.

---

## 4) Lógica de parcelamento implementada

- Ao lançar despesa no cartão (`add_card_transaction`), o sistema define automaticamente a fatura com base em data + dia de fechamento.
- Se `installment_total > 1`:
  - a transação mãe vira parcela `1/N` com valor parcelado;
  - parcelas `2..N` são criadas como transações filhas com `status='scheduled'` nas faturas dos meses seguintes;
  - total de cada fatura é recalculado após criação.

---

## 5) O que falta para a Fase 3 (Investimentos)

- Fluxo completo de investimentos: aportes, resgates, proventos e custo médio.
- Integração de posições por ativo/classe e carteira consolidada.
- Rentabilidade histórica (mensal/acumulada) e comparação com benchmark.
- Metas de alocação e rebalanceamento sugerido.
- Importação de extratos/notas e conciliação automática para investimentos.
- Relatórios específicos de patrimônio, risco e evolução da carteira.
