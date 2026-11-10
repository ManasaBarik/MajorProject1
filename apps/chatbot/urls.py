from django.urls import path
from .views import ChatView, ConversationsListView, ConversationDetailView

urlpatterns = [
    path("chatbot/chat/", ChatView.as_view()),
    path("chatbot/conversations/", ConversationsListView.as_view()),
    path("chatbot/conversations/<int:pk>/", ConversationDetailView.as_view()),
]
