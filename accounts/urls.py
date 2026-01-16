from django.urls import path
from .views import google_login_success

urlpatterns = [
    path("google/success/", google_login_success),
]
