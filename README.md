# FinanceFlow

Sistema de controle financeiro familiar em Django.

## Stack
- Python 3.12+
- Django 5.1
- PostgreSQL
- Redis
- Celery + Celery Beat
- Channels + Daphne
- TailwindCSS (CDN), HTMX, Alpine.js, Lucide, Chart.js

## Funcionalidades (ate Fase 2)
- Auth (registro, login, perfil, familia e convites)
- Dashboard com KPIs e graficos
- CRUD de contas e transacoes
- Transferencia entre contas
- Cartoes de credito com faturas e pagamento
- Parcelamento automatico em faturas futuras
- Orcamentos mensais com progresso
- Metas financeiras com aportes
- Relatorios basicos (12 meses, top categorias, pizza mensal)

## Estrutura
- `config/` settings e bootstrap Django/Celery
- `apps/` modulos de dominio
- `templates/` telas
- `static/` css/js
- `requirements/` dependencias por ambiente

## Setup rapido (local com Supabase + Redis local)
1. Criar e ativar virtualenv:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instalar dependencias:
```powershell
pip install -r requirements\development.txt
```

3. Criar `.env` (baseado em `.env.example`) e preencher credenciais do Supabase.

4. Subir Redis local (Docker):
```powershell
docker run -d --name financeflow-redis -p 6379:6379 redis:7-alpine
```

5. Rodar migrations e seed:
```powershell
python manage.py migrate
python manage.py seed_categories
```

6. Criar superusuario:
```powershell
python manage.py createsuperuser
```

7. Rodar servidor:
```powershell
python manage.py runserver
```

## Comandos uteis
```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py seed_categories
```

## Celery (opcional no dev)
```powershell
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Rotas principais
- App: `http://localhost:8000/`
- Login: `http://localhost:8000/auth/login/`
- Admin: `http://localhost:8000/admin/`

## Notas
- O projeto usa modelo de usuario customizado (`core.User`) com login por email.
- Para detalhes tecnicos e contexto por fase, veja `CONTEXTO.md`.
