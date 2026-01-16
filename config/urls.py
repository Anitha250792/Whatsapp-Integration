from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔐 Auth
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),

    # 🌐 Allauth (Google OAuth)
    path("accounts/", include("allauth.urls")),
    path("api/auth/", include("accounts.urls")),

]
