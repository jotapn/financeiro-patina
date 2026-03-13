# FinanceFlow

Plataforma de controle financeiro familiar em Django com contas, cartões, investimentos, automações e assistente IA via Ollama.

## Stack
- Python 3.12+
- Django 5.1
- PostgreSQL
- Redis
- Celery + Celery Beat
- Channels + Daphne
- TailwindCSS (CDN), HTMX, Alpine.js, Lucide, Chart.js
- Ollama + LangChain
- Tesseract OCR

## Funcionalidades
### Fase 1
- Auth completa com usuário por e-mail, perfil e grupo familiar
- Dashboard com KPIs, gráfico de fluxo e categorias
- CRUD de contas, transações e transferências
- Categorias padrão e layout glassmorphism

### Fase 2
- Cartões de crédito com faturas, pagamento parcial/total e parcelamento
- Orçamentos e metas financeiras
- Relatórios básicos

### Fase 3
- Carteira de investimentos com múltiplas classes de ativos
- Operações, preço médio, cotações e metas de investimento

### Fase 4
- Chat IA com widget flutuante + página completa em `/ai/`
- Seleção automática do modelo Ollama por RAM
- Streaming via Server-Sent Events
- Importação de extratos CSV (Nubank, Inter, Bradesco, genérico)
- OCR de comprovantes para pré-preenchimento de transações
- Transações recorrentes com Celery
- Notificações automáticas e comando central de setup do Beat
- Melhorias de responsividade, acessibilidade, toasts, modal de confirmação e scroll-to-top

## Setup local
### 1. Ambiente Python
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements\development.txt
```

### 2. Configuração
Copie `.env.example` para `.env` e preencha as credenciais do PostgreSQL/Supabase.

Variáveis novas:
- `OLLAMA_BASE_URL=http://ollama:11434`
- `REDIS_URL=redis://redis:6379/0`

### 3. Infraestrutura com Docker
```powershell
docker-compose up -d db redis ollama
```

### 4. Pull do modelo LLM
```powershell
python manage.py pull_llm_model
```

### 5. Migrations e seeds
```powershell
python manage.py migrate
python manage.py seed_categories
python manage.py seed_asset_classes
python manage.py setup_celery_beat
```

### 6. Subir a aplicação
```powershell
python manage.py runserver
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Setup automatizado
Em ambiente Unix-like:
```bash
chmod +x setup.sh
./setup.sh
```

## Comandos úteis
```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py pull_llm_model
python manage.py setup_celery_beat
python manage.py seed_categories
python manage.py seed_asset_classes
```

## Rotas principais
- `/` dashboard
- `/transactions/` transações
- `/transactions/import/` importação CSV
- `/cards/` cartões
- `/budgets/` orçamentos e metas
- `/reports/` relatórios
- `/investments/` carteira
- `/ai/` assistente IA
- `/admin/` administração

## Integrações externas
- `brapi.dev`: cotações B3
- `CoinGecko`: cotações de cripto
- `BCB SGS 12`: CDI diário
- `Ollama`: inferência local
- `Tesseract OCR`: extração de dados de comprovantes

## Observações
- O projeto usa `core.User` como modelo de autenticação.
- O assistente IA depende de Ollama disponível no `OLLAMA_BASE_URL`.
- Em Python 3.14, o LangChain atual emite warning de compatibilidade Pydantic v1, mas o projeto permanece funcional.
- Para detalhes técnicos por fase, veja `CONTEXTO.md`.
