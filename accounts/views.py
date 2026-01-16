from django.shortcuts import redirect
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.decorators import login_required

@login_required
def google_login_success(request):
    user = request.user
    refresh = RefreshToken.for_user(user)

    return redirect(
        f"https://whatsapp-integration-frontend-green.vercel.app/oauth-success"
        f"?access={refresh.access_token}&refresh={refresh}"
    )
