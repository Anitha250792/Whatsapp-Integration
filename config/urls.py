from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static


# ✅ simple success page (required because you set LOGIN_REDIRECT_URL)
def login_success(request):
    return HttpResponse("Login successful")


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # 🔐 Email / Password + JWT (dj-rest-auth)
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),

    # 🔐 Google & Facebook login (django-allauth)
    path("accounts/", include("allauth.urls")),

    # ✅ success redirect after social login
    path("accounts/success/", login_success),

    # 📁 File APIs
    path("files/", include("files.urls")),
]


# Media (only when DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
