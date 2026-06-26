from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/password-reset/', views.FinancePasswordResetView.as_view(), name='core_password_reset'),
    path('auth/password-reset/done/', views.FinancePasswordResetDoneView.as_view(), name='core_password_reset_done'),
    path(
        'auth/reset/<uidb64>/<token>/',
        views.FinancePasswordResetConfirmView.as_view(),
        name='core_password_reset_confirm',
    ),
    path('auth/reset/done/', views.FinancePasswordResetCompleteView.as_view(), name='core_password_reset_complete'),
    path('profile/', views.profile, name='profile'),
    path('profile/2fa/setup/', views.two_factor_setup, name='two_factor_setup'),
    path('profile/2fa/verify/', views.two_factor_challenge, name='two_factor_challenge'),
    path('profile/2fa/disable/', views.two_factor_disable, name='two_factor_disable'),
    path('family/', views.family_settings, name='family'),
    path('family/invite/', views.invite_member, name='invite_member'),
    path('family/accept/<uuid:token>/', views.accept_invite, name='accept_invite'),
]

