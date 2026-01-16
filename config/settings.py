"""
Django settings for config project.
"""

from pathlib import Path
import os
from datetime import timedelta

# --------------------------------------------------
# BASE DIR
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------
# SECURITY
# --------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-this-in-production")
DEBUG = False

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1"
).split(",")


# --------------------------------------------------
# APPLICATIONS
# --------------------------------------------------
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "dj_rest_auth",
    "dj_rest_auth.registration",

    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Local apps
    "accounts",
    "files",
    "pdf_tools",
]

# --------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# --------------------------------------------------
# AUTH / ALLAUTH CONFIG
# --------------------------------------------------
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "none"

SOCIALACCOUNT_LOGIN_ON_GET = True

LOGIN_REDIRECT_URL = "/accounts/google/success/"
LOGOUT_REDIRECT_URL = "/"



# --------------------------------------------------
# DJ-REST-AUTH
# --------------------------------------------------
REST_USE_JWT = True

REST_AUTH_REGISTER_SERIALIZERS = {
    "REGISTER_SERIALIZER": "dj_rest_auth.registration.serializers.RegisterSerializer",
}

# --------------------------------------------------
# JWT
# --------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --------------------------------------------------
# REST FRAMEWORK (ONLY ONCE!)
# --------------------------------------------------

REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": None,
    "JWT_AUTH_REFRESH_COOKIE": None,
}


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "dj_rest_auth.jwt_auth.JWTCookieAuthentication",
    ),
}



# --------------------------------------------------
# GOOGLE OAUTH
# --------------------------------------------------
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}


# --------------------------------------------------
# CORS
# --------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://whatsapp-integration-frontend-green.vercel.app",
]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = ["https://whatsapp-integration-frontend-green.vercel.app"]
SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True


# --------------------------------------------------
# URL / TEMPLATES
# --------------------------------------------------
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------
# DATABASE
# --------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --------------------------------------------------
# PASSWORD VALIDATION
# --------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------
# I18N
# --------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------
# STATIC / MEDIA
# --------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --------------------------------------------------
# DEFAULT FIELD
# --------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
