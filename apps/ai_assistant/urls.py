from django.urls import path

from . import views

urlpatterns = [
    path('', views.chat_home, name='ai_chat_home'),
    path('new/', views.create_session, name='ai_create_session'),
    path('chat/stream/', views.chat_stream, name='ai_chat_stream'),
    path('sessions/', views.session_list, name='ai_session_list'),
    path('sessions/<int:pk>/', views.session_detail, name='ai_session_detail'),
    path('sessions/<int:pk>/export/', views.export_session_pdf, name='ai_export_session_pdf'),
    path('widget/', views.widget_context, name='ai_widget_context'),
]
