from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔐 dj-rest-auth
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),

    # 🔑 SOCIAL LOGIN (THIS CREATES /api/auth/google/)
    path("api/auth/", include("dj_rest_auth.social_urls")),

    # allauth
    path("accounts/", include("allauth.urls")),
]
