"""Routes for account and authentication endpoints."""

from __future__ import annotations

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("profile/", views.profile, name="profile"),
    path("generate-2fa/", views.generate_2fa, name="generate-2fa"),
    path("password-reset-request/", views.password_reset_request, name="password-reset-request"),
    path("password-reset-confirm/", views.password_reset_confirm, name="password-reset-confirm"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
