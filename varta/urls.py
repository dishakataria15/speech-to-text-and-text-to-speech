from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('auth/', views.auth_page, name='auth'),
    path('conversation/', views.conversation_view, name='conversation'),
    path('history/', views.history_view, name='history'),
    path('quick-responses/', views.quick_responses_view, name='quick_responses'),
    path('quick-responses/delete/<int:response_id>/', views.delete_quick_response, name='delete_quick_response'),
    path('logout/', views.logout_view, name='logout'),
    
    # API endpoints
    path('translate-text/', views.translate_text, name='translate_text'),
    path('text-to-speech/', views.text_to_speech, name='text_to_speech'),
    path('save-conversation/', views.save_conversation, name='save_conversation'),
    path('get-conversation-history/', views.get_conversation_history, name='get_conversation_history'),
    path('clear-conversation-history/', views.clear_conversation_history, name='clear_conversation_history'),
]