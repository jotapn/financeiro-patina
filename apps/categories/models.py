from django.db import models


class Category(models.Model):
    TYPE_CHOICES = [('income', 'Receita'), ('expense', 'Despesa')]

    family_group = models.ForeignKey(
        'core.FamilyGroup', null=True, blank=True, on_delete=models.CASCADE, related_name='categories'
    )
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    icon = models.CharField(max_length=50, default='tag')
    color = models.CharField(max_length=7, default='#7c3aed')
    is_system = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Categoria'

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Subcategoria'

    def __str__(self):
        return f'{self.category.name} > {self.name}'

