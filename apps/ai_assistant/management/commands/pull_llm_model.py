from django.core.management.base import BaseCommand

from apps.ai_assistant.llm_manager import pull_model


class Command(BaseCommand):
    help = 'Baixa o melhor modelo Ollama com base na RAM disponível'

    def handle(self, *args, **options):
        model, updates = pull_model()
        self.stdout.write(self.style.SUCCESS(f'Modelo selecionado: {model}'))
        for update in updates[-5:]:
            self.stdout.write(update)
