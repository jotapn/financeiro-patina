from django.urls import path

from . import views

urlpatterns = [
    path('', views.card_list, name='card_list'),
    path('create/', views.card_create, name='card_create'),
    path('<int:pk>/', views.card_detail, name='card_detail'),
    path('<int:pk>/pay/', views.pay_invoice, name='pay_invoice'),
    path('<int:card_pk>/add-transaction/', views.add_card_transaction, name='add_card_transaction'),
]
