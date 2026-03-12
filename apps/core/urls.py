from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('family/', views.family_settings, name='family'),
    path('family/invite/', views.invite_member, name='invite_member'),
    path('family/accept/<uuid:token>/', views.accept_invite, name='accept_invite'),
]

