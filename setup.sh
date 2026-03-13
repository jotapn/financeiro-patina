#!/bin/bash
set -e

echo "Iniciando FinanceFlow..."

docker-compose up -d db redis ollama

echo "Aguardando Ollama inicializar (30s)..."
sleep 30

RAM_GB=$(docker exec financeflow-ollama-1 sh -c "awk '/MemTotal/ {print int($2/1024/1024)}' /proc/meminfo")

if [ "$RAM_GB" -ge 16 ]; then
    MODEL="llama3.1:8b-instruct-q4_K_M"
elif [ "$RAM_GB" -ge 8 ]; then
    MODEL="mistral:7b-instruct-q4_K_M"
else
    MODEL="gemma2:2b-instruct"
fi

echo "Baixando modelo: $MODEL (RAM: ${RAM_GB}GB)"
docker exec financeflow-ollama-1 ollama pull $MODEL

docker-compose up -d

docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_categories
docker-compose exec web python manage.py seed_asset_classes
docker-compose exec web python manage.py setup_celery_beat

echo "Crie o superusuário manualmente com: docker-compose exec web python manage.py createsuperuser"
echo "FinanceFlow rodando em http://localhost:8000"
echo "Documentação: README.md"
