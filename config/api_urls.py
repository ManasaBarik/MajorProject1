from django.urls import include, path

urlpatterns = [
 path("", include("apps.accounts.urls")), path("", include("apps.departments.urls")), path("", include("apps.services.urls")),
 path("", include("apps.complaints.urls")), path("", include("apps.businesses.urls")), path("", include("apps.applications.urls")),
 path("", include("apps.notifications.urls")), path("", include("apps.analytics.urls")), path("", include("apps.chatbot.urls")), path("", include("apps.audit.urls")),
]
