from django.urls import path
from .views import AuditView

urlpatterns = [
    path("audit-logs/", AuditView.as_view()),
]
