from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔐 dj-rest-auth (JWT login / logout)
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),

    # 🌐 Allauth (Google OAuth)
    path("accounts/", include("allauth.urls")),

    # 📁 File APIs
    path("api/files/", include("files.urls")),
]

# 📂 Media files (uploads)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
