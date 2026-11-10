from django.urls import path
from .views import (
    RegisterView, LoginView, RefreshView, MeView, LogoutView,
    PasswordResetView, PasswordResetConfirmView,
    AdminUserListView, AdminUserUpdateView, AdminOfficerListView,
    AdminOfficerDetailView, AdminEngineerListView, AdminEngineerDetailView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/token/refresh/", RefreshView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("auth/password-reset/", PasswordResetView.as_view()),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view()),
    path("users/me/", MeView.as_view()),
    path("users/", AdminUserListView.as_view()),
    path("users/<int:pk>/", AdminUserUpdateView.as_view()),
    path("admin/officers/", AdminOfficerListView.as_view()),
    path("admin/officers/<int:pk>/", AdminOfficerDetailView.as_view()),
    path("admin/engineers/", AdminEngineerListView.as_view()),
    path("admin/engineers/<int:pk>/", AdminEngineerDetailView.as_view()),
]
