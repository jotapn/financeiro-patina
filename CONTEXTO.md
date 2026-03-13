# CONTEXTO - FinanceFlow (Fase 4)

## 1) Models criados/atualizados

### apps.core
- `User`, `FamilyGroup`, `UserProfile`, `FamilyInvitation`.

### apps.accounts
- `FinancialAccount`, `PaymentMethod`.

### apps.transactions
- `Tag`, `RecurrenceRule`, `Transaction`.
- Novos fluxos de Fase 4:
  - importação CSV via `CSVImporter`
  - OCR de comprovantes via `extract_receipt_data`
  - recorrência automática via task `create_scheduled_transactions`

### apps.cards
- `CreditCard`, `CardInvoice` (com `payment_transaction`).
- Nova task: `generate_monthly_invoices`.

### apps.categories
- `Category`, `Subcategory`.

### apps.budgets
- `Budget`, `FinancialGoal`, `GoalContribution`.

### apps.investments
- `AssetClass`
- `Investment`
- `InvestmentTransaction`
- `InvestmentGoal`

### apps.ai_assistant
- `AiAssistantLog`
- `ChatSession`: sessão de conversa por usuário
- `ChatMessage`: mensagens do usuário/assistente

### apps.notifications
- `Notification`: agora com `notification_type`, `action_url`, `is_read`, `created_at`

---

## 2) URLs disponíveis

### config/urls.py
- `/admin/`
- `/`
- `/auth/`
- `/accounts/`
- `/transactions/`
- `/cards/`
- `/categories/`
- `/budgets/`
- `/reports/`
- `/investments/`
- `/ai/`

### apps.ai_assistant.urls
- `/ai/` (`ai_chat_home`)
- `/ai/new/` (`ai_create_session`)
- `/ai/chat/stream/` (`ai_chat_stream`)
- `/ai/sessions/` (`ai_session_list`)
- `/ai/sessions/<id>/` (`ai_session_detail`)
- `/ai/sessions/<id>/export/` (`ai_export_session_pdf`)
- `/ai/widget/` (`ai_widget_context`)

### apps.transactions.urls
- `/transactions/import/` (`import-csv`)
- `/transactions/ocr/` (`ocr-receipt`)
- `/transactions/<id>/confirm/` (`confirm_scheduled`)
- rotas existentes de list/create/edit/delete/toggle-status

---

## 3) Decisões técnicas importantes
- Assistente IA implementado sobre `Ollama` + `LangChain tools`, com seleção automática de modelo via RAM em `llm_manager.py`.
- O “agente” usa tools reais do domínio financeiro e monta contexto objetivo antes de chamar o modelo.
- Streaming de resposta implementado com SSE em `chat_stream`.
- Widget global e página full do chat compartilham a mesma lógica Alpine/JS.
- Importação CSV foi desenhada para preview + detecção de duplicata antes de persistir.
- OCR usa `pytesseract` e pré-processamento simples com Pillow.
- Recorrência usa `Transaction.parent_transaction` + `RecurrenceRule.occurrences_created`.
- Notificações seguem modelo simples com `action_url` para deep-link no frontend.
- `setup_celery_beat` centraliza os schedules operacionais da aplicação.

---

## 4) APIs externas integradas
- `brapi.dev` para ações/FII/ETF/BDR.
- `CoinGecko` para cripto.
- `Banco Central (BCB SGS 12)` para CDI diário.
- `Ollama API` para inferência local e pull de modelo.
- `Tesseract OCR` para leitura de comprovantes.

---

## 5) Celery tasks configuradas

### apps.investments.tasks
- `update_stock_prices`
- `update_crypto_prices`
- `update_fixed_income_returns`
- `setup_investment_schedules`

### apps.notifications.tasks
- `check_all_alerts`

### apps.transactions.tasks
- `create_scheduled_transactions`

### apps.cards.tasks
- `generate_monthly_invoices`

### setup_celery_beat
Schedules criados:
- ações: 15 em 15 min em dias úteis
- cripto: 5 em 5 min
- renda fixa: diário às 20h
- alertas: diário às 8h
- recorrentes: diário às 7h
- faturas: dia 1 às 00:30

---

## 6) Comandos executados na Fase 4
- `pip install -r requirements/development.txt`
- `python manage.py makemigrations ai_assistant notifications --noinput`
- `python manage.py migrate`
- `python manage.py check`
- `python manage.py setup_celery_beat`
- `python manage.py seed_asset_classes`

---

## 7) O que falta depois da Fase 4
- Exportações avançadas por módulo em formatos reais como XLSX/PDF com layout rico.
- Observabilidade operacional mais robusta para Celery e integrações externas.
- Políticas mais finas de autorização por papel no ambiente familiar.
- Melhorias de qualidade para o agente IA com memory, ranking semântico e chamadas mais sofisticadas de ferramentas.
