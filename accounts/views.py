from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from django.http import HttpResponse
from .models import UserProfile
from django.core.exceptions import ValidationError
from django.db import transaction
from files.whatsapp_utils import send_whatsapp_linking_instructions

import requests
import re

User = get_user_model()

class GoogleLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response({"error": "Token missing"}, status=400)

        try:
            info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.SOCIALACCOUNT_PROVIDERS["google"]["CLIENT_ID"],
            )
        except ValueError:
            return Response({"error": "Invalid token"}, status=400)

        email = info.get("email")
        name = info.get("name", "")

        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "first_name": name},
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": user.email,
        })
    
def privacy_policy(request):
    return HttpResponse(
        """
        <h1>Privacy Policy</h1>
        <p>This application uses social login (Google and Facebook) only for authentication.</p>
        <p>No personal data is shared with third parties.</p>
        """
    )

def terms_of_service(request):
    return HttpResponse(
        """
        <h1>Terms of Service</h1>
        <p>This application is intended for file integration and authentication purposes only.</p>
        """
    )

def data_deletion_view(request):
    return HttpResponse(
        """
        <h1>User Data Deletion</h1>
        <p>
        To delete your account and associated data, please email:
        <b>ntanithasaravanan@gmail.com</b> using your registered email.
        </p>
        """
    )

class FacebookLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        access_token = request.data.get("access_token")

        if not access_token:
            return Response({"error": "Access token missing"}, status=400)

        fb_url = "https://graph.facebook.com/me"
        params = {
            "fields": "id,name,email",
            "access_token": access_token,
        }

        fb_res = requests.get(fb_url, params=params)
        data = fb_res.json()

        if "error" in data:
            return Response({"error": "Invalid Facebook token"}, status=400)

        email = data.get("email")
        name = data.get("name", "")

        if not email:
            return Response(
                {"error": "Facebook account has no email"},
                status=400
            )

        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "first_name": name},
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "email": user.email,
        })
    

class UpdateWhatsAppView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        number = request.data.get("whatsapp_number", "").strip()
        enabled = bool(request.data.get("whatsapp_enabled", False))

        # ✅ Validate number only if enabled
        if enabled:
            if not re.fullmatch(r"\+[1-9]\d{7,14}", number):
                return Response(
                    {
                        "error": "Enter WhatsApp number with country code (e.g. +919876543210)"
                    },
                    status=400,
                )

        try:
            with transaction.atomic():
                profile, _ = UserProfile.objects.get_or_create(
                    user=request.user
                )

                profile.whatsapp_number = number
                profile.whatsapp_enabled = enabled
                profile.save()

            return Response(
                {"message": "WhatsApp settings updated successfully"},
                status=200,
            )

        except Exception as e:
            print("❌ UpdateWhatsAppView error:", str(e))
            return Response(
                {"error": "Failed to update WhatsApp settings"},
                status=500,
            )