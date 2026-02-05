from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as account_views

urlpatterns = [
    path("privacy-policy/", account_views.privacy_policy),
    path("terms/", account_views.terms_of_service),
    path("data-deletion/", account_views.data_deletion_view),
    path("admin/", admin.site.urls),

    # 🔐 AUTH
    path("dj-rest-auth/", include("dj_rest_auth.urls")),
    path("dj-rest-auth/registration/", include("dj_rest_auth.registration.urls")),

    # 🔐 JWT auth (email/password)
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),

    # 🔐 Google JWT login (custom API)
    path("accounts/", include("accounts.urls")),

    # 📁 File APIs (NO /api)
    path("files/", include("files.urls")),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
