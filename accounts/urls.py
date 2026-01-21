from django.urls import path
from .views import GoogleLoginAPIView
from .views import privacy_policy, terms_of_service, data_deletion_view



urlpatterns = [
    path("google/", GoogleLoginAPIView.as_view()),
    path("privacy-policy/", privacy_policy, name="privacy_policy"),
    path("terms/", terms_of_service, name="terms"),
    path("data-deletion/", data_deletion_view),
]
