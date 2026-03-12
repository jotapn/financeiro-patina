from django.urls import path

from . import views

urlpatterns = [
    path('', views.portfolio_dashboard, name='portfolio_dashboard'),
    path('list/', views.investment_list, name='investment_list'),
    path('create/', views.investment_create, name='investment_create'),
    path('<int:pk>/', views.investment_detail, name='investment_detail'),
    path('<int:pk>/add-transaction/', views.investment_add_transaction, name='investment_add_transaction'),
    path('goals/create/', views.investment_goal_create, name='investment_goal_create'),
    path('refresh/', views.refresh_prices, name='refresh_prices'),
]
