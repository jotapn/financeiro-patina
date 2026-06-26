from django.urls import path

from . import views

urlpatterns = [
    path('', views.pluggy_list, name='pluggy_list'),
    path('connect/', views.pluggy_connect, name='pluggy_connect'),
    path('callback/', views.pluggy_callback, name='pluggy_callback'),
    path('confirm/<int:item_pk>/', views.pluggy_confirm, name='pluggy_confirm'),
    path('<int:item_pk>/sync/', views.pluggy_sync_now, name='pluggy_sync_now'),
    path('<int:item_pk>/disconnect/', views.pluggy_disconnect, name='pluggy_disconnect'),
    path('webhook/', views.pluggy_webhook, name='pluggy_webhook'),
]
