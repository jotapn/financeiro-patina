from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Category


@login_required
def category_list(request):
    group = request.user.profile.family_group
    categories = Category.objects.filter(family_group=group) | Category.objects.filter(is_system=True)
    return render(request, 'categories/list.html', {'categories': categories.order_by('name')})


@login_required
def create_default_transfer_category(request):
    if request.method == 'POST':
        Category.objects.get_or_create(
            family_group=None,
            name='Transferência',
            category_type='expense',
            defaults={'is_system': True, 'icon': 'repeat', 'color': '#64748b', 'sort_order': 999},
        )
        messages.success(request, 'Categoria de transferência garantida.')
    return redirect('category_list')

