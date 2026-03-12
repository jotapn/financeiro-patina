from django.urls import path

from . import views

urlpatterns = [
    path('', views.budget_list, name='budget_list'),
    path('create/', views.budget_create, name='budget_create'),
    path('clone/', views.budget_clone, name='budget_clone'),
    path('goals/create/', views.goal_create, name='goal_create'),
    path('goals/<int:pk>/contribute/', views.goal_contribute, name='goal_contribute'),
]
