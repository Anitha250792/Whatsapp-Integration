from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔐 JWT auth (email/password)
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),

    # 🔐 Allauth (Google / Facebook)
    path("accounts/", include("allauth.urls")),

    # 🔐 Custom account APIs + privacy/terms pages
    path("", include("accounts.urls")),

    # 📁 File APIs
    path("files/", include("files.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
