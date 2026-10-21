"""
Production settings for Don Corleone Backend.

Required environment variables:
- DJANGO_SECRET_KEY: long random secret (never the development default)
- ALLOWED_HOSTS: comma-separated API domains (e.g. api.doncorleonepizzas.com.br)
- DATABASE_URL: PostgreSQL connection string
Optional: CORS_ALLOWED_ORIGINS, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS.
"""
from django.core.exceptions import ImproperlyConfigured
from .base import *
import os


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"A variável de ambiente {name} é obrigatória em produção.")
    return value


def _env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


DEBUG = False

SECRET_KEY = _required_env("DJANGO_SECRET_KEY")
if SECRET_KEY.startswith("don-corleone-dev-secret-key"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY de produção não pode ser a chave de desenvolvimento.")

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Defina ALLOWED_HOSTS com os domínios da API (sem '*').")

# Database URL support for PostgreSQL (Render, Railway, Fly.io, Neon, Supabase)
import dj_database_url
DATABASES = {
    "default": dj_database_url.config(default=_required_env("DATABASE_URL"), conn_max_age=600)
}

# Static files served by WhiteNoise (right after SecurityMiddleware)
MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True") == "True"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "3600"))
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = _env_list(
    "CORS_ALLOWED_ORIGINS", "https://doncorleonepizzas.com.br,https://www.doncorleonepizzas.com.br"
)
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Request-throttling counters shared by all gunicorn workers (the default memory cache is per process)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.getenv("DJANGO_CACHE_DIR", "/srv/cache"),
    }
}

# Errors go to the container logs (`docker compose logs web`); Django's default only emails admins
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
