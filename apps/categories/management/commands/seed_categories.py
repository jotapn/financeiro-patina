from django.core.management.base import BaseCommand

from apps.categories.models import Category, Subcategory

CATEGORIES = {
    'expense': [
        ('Moradia', 'home', '#3b82f6', 1, ['Aluguel', 'Condomínio', 'IPTU', 'Água', 'Luz', 'Gás', 'Internet', 'Manutenção']),
        ('Alimentação', 'utensils', '#f59e0b', 2, ['Supermercado', 'Restaurante', 'Delivery', 'Padaria', 'Feira']),
        ('Transporte', 'car', '#06b6d4', 3, ['Combustível', 'Uber/99', 'Ônibus/Metrô', 'Estacionamento', 'IPVA', 'Seguro Auto']),
        ('Saúde', 'heart-pulse', '#ef4444', 4, ['Plano de Saúde', 'Farmácia', 'Consulta', 'Exame', 'Academia']),
        ('Educação', 'book-open', '#8b5cf6', 5, ['Mensalidade', 'Cursos', 'Livros', 'Material Escolar']),
        ('Lazer', 'smile', '#ec4899', 6, ['Cinema/Teatro', 'Streaming', 'Viagens', 'Esportes', 'Hobbies']),
        ('Vestuário', 'shirt', '#f97316', 7, ['Roupas', 'Calçados', 'Acessórios']),
        ('Assinaturas', 'smartphone', '#7c3aed', 8, ['Netflix', 'Spotify', 'Amazon Prime', 'iCloud', 'Adobe', 'Outros']),
        ('Pets', 'paw-print', '#84cc16', 9, ['Ração', 'Veterinário', 'Pet Shop', 'Banho e Tosa']),
        ('Impostos/Taxas', 'receipt', '#64748b', 10, ['Imposto de Renda', 'IPVA', 'IPTU', 'IOF']),
        ('Pessoal', 'user', '#0ea5e9', 11, ['Cabelo', 'Beleza', 'Higiene', 'Barbeiro']),
        ('Transferência', 'repeat', '#64748b', 12, []),
        ('Outros', 'package', '#94a3b8', 13, []),
    ],
    'income': [
        ('Salário', 'briefcase', '#10b981', 1, ['Salário', '13° Salário', 'Férias', 'PLR', 'Bônus']),
        ('Freelance', 'laptop', '#3b82f6', 2, ['Projeto', 'Consultoria', 'Prestação de Serviço']),
        ('Investimentos', 'trending-up', '#7c3aed', 3, ['Dividendos', 'JCP', 'Rendimento CDB', 'Rendimento FII', 'Cripto']),
        ('Aluguel Recebido', 'building', '#f59e0b', 4, []),
        ('Presente/Doação', 'gift', '#ec4899', 5, []),
        ('Reembolso', 'rotate-ccw', '#06b6d4', 6, []),
        ('Outros', 'plus-circle', '#94a3b8', 7, []),
    ],
}


class Command(BaseCommand):
    help = 'Popula as categorias padrão do sistema'

    def handle(self, *args, **options):
        created = 0
        for cat_type, categories in CATEGORIES.items():
            for name, icon, color, order, subcats in categories:
                cat, is_new = Category.objects.get_or_create(
                    name=name,
                    category_type=cat_type,
                    family_group=None,
                    defaults={
                        'icon': icon,
                        'color': color,
                        'is_system': True,
                        'sort_order': order,
                    },
                )
                if is_new:
                    created += 1
                for sub_name in subcats:
                    Subcategory.objects.get_or_create(category=cat, name=sub_name)

        self.stdout.write(self.style.SUCCESS(f'Categorias criadas: {created}'))

