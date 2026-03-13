from django.urls import path

from . import views

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('create/', views.transaction_create, name='transaction_create'),
    path('import/', views.import_csv, name='import-csv'),
    path('ocr/', views.ocr_receipt, name='ocr-receipt'),
    path('<int:id>/confirm/', views.confirm_scheduled, name='confirm_scheduled'),
    path('<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('<int:pk>/toggle-status/', views.toggle_status, name='toggle_status'),
]
