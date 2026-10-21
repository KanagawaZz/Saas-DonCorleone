"""
Base settings for Don Corleone Backend project.
"""
from pathlib import Path
import os
import sys
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# The project's .env (repo root) is shared with docker-compose (Evolution API key, etc.).
# Real environment variables win over the file.
load_dotenv(BASE_DIR.parent / ".env")
APPS_DIR = BASE_DIR / "apps"
sys.path.insert(0, str(APPS_DIR))

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "don-corleone-dev-secret-key-change-in-production-123456789")

DEBUG = False

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    # Django Core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",

    # Local Apps (Domain modules)
    "apps.core",
    "apps.accounts",
    "apps.tenants",
    "apps.catalog",
    "apps.pricing",
    "apps.delivery",
    "apps.customers",
    "apps.orders",
    "apps.promotions",
    "apps.tracking",
    "apps.printing",
    "apps.integrations",
    "apps.painel",
]

# Public website address: menu photos (/images/cardapio/...) live there, not in the backend
SITE_PUBLIC_URL = os.getenv("SITE_PUBLIC_URL", "http://localhost:3000").rstrip("/")

# Owner's panel login (Django session)
LOGIN_URL = "painel:entrar"
LOGIN_REDIRECT_URL = "painel:dashboard"
LOGOUT_REDIRECT_URL = "painel:entrar"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Last: friendly error page + occurrence code for unexpected errors raised by views
    "apps.core.middleware.ErrorTrackingMiddleware",
]

# WhatsApp that receives an alert for each new kind of unexpected error (empty = no alert)
SUPPORT_WHATSAPP = os.getenv("SUPPORT_WHATSAPP", "")

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
ASGI_APPLICATION = "config.asgi.application"

# Database defaults to SQLite in local
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization & Cuiaba Timezone
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Cuiaba"
USE_I18N = True
USE_TZ = True

# Static & Media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DATETIME_FORMAT": "%d/%m/%Y %H:%M",
    # Public endpoints opt in with `throttle_scope`
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "orders": "20/min",
        "tracking": "30/min",
        "auth": "10/min",
    },
}

# CORS configuration: closed by default; local.py opens it, production.py lists the allowed domains
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

# Evolution API (WhatsApp automatic notification), run with docker-compose.yml.
# The key is the server's master key; each store's instance name is chosen in the panel.
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8081").rstrip("/")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
# Default instance name until the store picks one in the panel
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "doncorleone")
