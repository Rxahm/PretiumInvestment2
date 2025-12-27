"""REST API views for authentication and account utilities."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Dict, Optional

import pyotp
import qrcode
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.throttling import AnonRateThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserSerializer
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import PasswordResetTokenGenerator
import os
from django.core.mail import send_mail

User = get_user_model()


def _issue_tokens(user: User) -> Dict[str, str]:
    """Return a dict containing refresh and access JWT tokens for ``user``."""

    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """Create a new user account."""

    username = (request.data.get("username") or "").strip()
    email = (request.data.get("email") or "").strip()
    password = request.data.get("password") or ""
    role = (request.data.get("role") or "owner").lower()

    if not username or not email or not password:
        return Response(
            {"error": "Username, email, and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if role not in {choice[0] for choice in User.ROLE_CHOICES}:
        return Response(
            {"error": "Role must be one of: owner, accountant."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "Username already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "Email already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        role=role,
    )

    serialized = UserSerializer(user)
    return Response(serialized.data, status=status.HTTP_201_CREATED)


class LoginThrottle(AnonRateThrottle):
    rate = "10/min"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login_view(request):
    """Authenticate a user and return JWT tokens."""

    username = request.data.get("username")
    password = request.data.get("password")
    token = (request.data.get("token") or "").strip()

    if not username or not password:
        return Response(
            {"error": "Username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)

    if user is None:
        return Response({"error": "Invalid username or password."}, status=status.HTTP_401_UNAUTHORIZED)

    if user.two_factor_secret:
        if not token:
            return Response(
                {"error": "Two-factor token is required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(token, valid_window=1):
            return Response({"error": "Invalid 2FA token."}, status=status.HTTP_401_UNAUTHORIZED)

    return Response(_issue_tokens(user), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    """Return profile information for the authenticated user."""

    serialized = UserSerializer(request.user)
    data = serialized.data
    data.pop("two_factor_secret", None)
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_2fa(request):
    """Generate or return an existing 2FA secret for the authenticated user."""

    user: User = request.user

    if not user.two_factor_secret:
        user.two_factor_secret = pyotp.random_base32()
        user.save(update_fields=["two_factor_secret"])

    totp = pyotp.TOTP(user.two_factor_secret)
    otp_uri = totp.provisioning_uri(name=user.email or user.username, issuer_name="Pretium Investment")

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(otp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return Response(
        {
            "otp_uri": otp_uri,
            "qr_code_base64": img_base64,
        }
    )


class PasswordResetThrottle(AnonRateThrottle):
    rate = "5/min"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset_request(request):
    """Initiate a password reset flow for the provided email.

    Always returns a 200 to avoid leaking whether the email exists. When
    DEBUG is enabled (or EXPOSE_RESET_TOKENS=true), the response includes a
    one-time reset token and uid to facilitate local development.
    """

    email = (request.data.get("email") or "").strip()
    if not email:
        return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

    user: Optional[User] = User.objects.filter(email__iexact=email).first()

    # Build a generic success payload
    payload: Dict[str, str] = {
        "status": "ok",
        "message": "If an account exists for that email, a reset link will be sent.",
    }

    if user is not None:
        token_gen = PasswordResetTokenGenerator()
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_gen.make_token(user)

        # Build reset URL for email delivery
        default_base = "http://localhost:3000/reset-password" if settings.DEBUG else "https://pretiuminvestment.com/reset-password"
        base = os.getenv("FRONTEND_RESET_URL_BASE", default_base)
        reset_url = f"{base}?uid={uidb64}&token={token}"

        # Send email if email backend is configured
        try:
            send_mail(
                subject="Password reset for Pretium Investment",
                message=(
                    "You requested a password reset.\n\n"
                    f"Use this link to set a new password: {reset_url}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            # Ignore email errors; still return generic message
            pass

        # Optionally include token for local/dev usage
        expose = (os.getenv("EXPOSE_RESET_TOKENS", "false").lower() in {"1", "true", "yes", "on"})
        if settings.DEBUG or expose:
            payload.update({"uid": uidb64, "token": token, "reset_url": reset_url})
    
    return Response(payload, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """Complete the password reset by validating token and setting a new password."""

    uidb64 = (request.data.get("uid") or "").strip()
    token = (request.data.get("token") or "").strip()
    new_password = request.data.get("new_password") or ""

    if not uidb64 or not token or not new_password:
        return Response(
            {"error": "uid, token, and new_password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

    token_gen = PasswordResetTokenGenerator()
    if not token_gen.check_token(user, token):
        return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

    # Optionally enforce minimum length via validators here if desired
    if len(new_password) < 8:
        return Response({"error": "Password must be at least 8 characters."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    return Response({"status": "ok"}, status=status.HTTP_200_OK)
