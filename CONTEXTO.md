# CONTEXTO - FinanceFlow (Fase 3)

## 1) Models criados/atualizados (campos principais)

### apps.core
- `User`, `FamilyGroup`, `UserProfile`, `FamilyInvitation`.

### apps.accounts
- `FinancialAccount`, `PaymentMethod`.

### apps.transactions
- `Tag`, `RecurrenceRule`, `Transaction`.

### apps.cards
- `CreditCard`, `CardInvoice` (com `payment_transaction`).

### apps.categories
- `Category`, `Subcategory`.

### apps.budgets
- `Budget`, `FinancialGoal`, `GoalContribution`.

### apps.investments (Fase 3)
- `AssetClass`: classe/tipo de ativo, cor, ícone, liquidez, tributação.
- `Investment`: ativo com preço médio/atual, quantidade, rentabilidade, renda fixa, cache de valores e recálculo.
- `InvestmentTransaction`: compra, venda, dividendos, JCP, rendimento, split/grupamento.
- `InvestmentGoal`: metas de investimento por ativo ou classe.

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
- `/investments/` + `apps.investments.urls`

### apps.investments.urls
- `/investments/` (`portfolio_dashboard`)
- `/investments/list/` (`investment_list`)
- `/investments/create/` (`investment_create`)
- `/investments/<int:pk>/` (`investment_detail`)
- `/investments/<int:pk>/add-transaction/` (`investment_add_transaction`)
- `/investments/goals/create/` (`investment_goal_create`)
- `/investments/refresh/` (`refresh_prices`)

---

## 3) Decisões técnicas importantes

- Fase 3 adicionou carteira de investimentos com múltiplas classes de ativos.
- Recálculo automático de posição e preço médio em `InvestmentTransaction.save()`.
- Dashboard de portfólio com KPI, alocação, top gainers/losers e metas de investimento.
- Atualização manual e automática de cotações preparada com Celery tasks.
- Link de Investimentos ativado na sidebar e integração completa de rotas.

---

## 4) APIs externas integradas

- `brapi.dev` para cotações de ações/FII/ETF/BDR (`update_stock_prices`).
- `CoinGecko` para cotações de cripto (`update_crypto_prices`).
- `Banco Central (BCB SGS 12)` para CDI diário (`update_fixed_income_returns`).

---

## 5) Celery tasks configuradas

### `apps.investments.tasks`
- `update_stock_prices` (B3 via brapi)
- `update_crypto_prices` (CoinGecko)
- `update_fixed_income_returns` (CDI/BCB para renda fixa)
- `setup_investment_schedules` (cria/agenda PeriodicTasks no Celery Beat)

Schedules configurados:
- B3: a cada 15 min em dias úteis (9h-18h)
- Cripto: a cada 5 min
- Renda fixa: 1x por dia útil às 18:30

---

## 6) Comandos executados na Fase 3

- `python manage.py makemigrations investments --noinput`
- `python manage.py migrate`
- `python manage.py seed_asset_classes`
- `python manage.py shell -c "from apps.investments.tasks import setup_investment_schedules; setup_investment_schedules()"`
- `python manage.py check`

---

## 7) O que falta para a Fase 4 (IA + notificações + exportações)

- Assistente IA com insights financeiros personalizados (chat e recomendações acionáveis).
- Motor de notificações inteligentes (limites, vencimentos, anomalias, metas e portfolio alerts).
- Exportação de dados e relatórios (CSV, XLSX, PDF) por módulo e período.
- Consolidação de automações (rotinas, monitoramento, retry strategy e observabilidade).
- Camada de permissões/políticas mais avançada para operação familiar compartilhada.
