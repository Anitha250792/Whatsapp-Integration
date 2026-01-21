from django.urls import path
from .views import GoogleLoginAPIView
from .views import privacy_policy, terms_of_service
from .views import SocialJWTView

urlpatterns = [
    path("google/", GoogleLoginAPIView.as_view(), name="google_login"),
    path("privacy-policy/", privacy_policy, name="privacy_policy"),
    path("terms/", terms_of_service, name="terms"),
    path("social-jwt/", SocialJWTView.as_view(), name="social_jwt"),
]
