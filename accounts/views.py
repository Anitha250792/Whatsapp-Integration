from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from django.http import HttpResponse

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
    return HttpResponse("""
        <h1>Privacy Policy</h1>
        <p>This application uses social login (Google and Facebook) only for authentication.</p>
        <p>No personal data is shared with third parties.</p>
    """)

def terms_of_service(request):
    return HttpResponse("""
        <h1>Terms of Service</h1>
        <p>This application is intended for file integration and authentication purposes only.</p>
    """)


    
    
