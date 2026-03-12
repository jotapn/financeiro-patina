from django.urls import path

from . import views

urlpatterns = [
    path('', views.category_list, name='category_list'),
    path('ensure-transfer/', views.create_default_transfer_category, name='ensure_transfer_category'),
]

