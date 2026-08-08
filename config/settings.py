from pathlib import Path
import os
import sys

import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [x.strip() for x in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if x.strip()]
AUTO_PUBLISH_LISTINGS = os.getenv("AUTO_PUBLISH_LISTINGS", "False").lower() == "true"
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
VERIFICATION_DEBUG_CODE = os.getenv("VERIFICATION_DEBUG_CODE", str(DEBUG)).lower() == "true"
SMS_WEBHOOK_URL = os.getenv("SMS_WEBHOOK_URL", "").strip()
SMS_WEBHOOK_TOKEN = os.getenv("SMS_WEBHOOK_TOKEN", "").strip()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
REVERSE_GEOCODING_ENABLED = os.getenv("REVERSE_GEOCODING_ENABLED", "False").lower() == "true"
REVERSE_GEOCODING_URL = os.getenv(
    "REVERSE_GEOCODING_URL",
    "https://nominatim.openstreetmap.org/reverse",
).strip()
REVERSE_GEOCODING_USER_AGENT = os.getenv(
    "REVERSE_GEOCODING_USER_AGENT",
    "IlanSehri/1.25.2",
).strip()
REVERSE_GEOCODING_TIMEOUT = float(
    os.getenv("REVERSE_GEOCODING_TIMEOUT", "6")
)
AI_LISTING_API_URL = os.getenv("AI_LISTING_API_URL", "").strip()
AI_LISTING_API_KEY = os.getenv("AI_LISTING_API_KEY", "").strip()
AI_LISTING_MODEL = os.getenv("AI_LISTING_MODEL", "vision-model").strip()

IS_TESTING = "test" in sys.argv
IS_CODESPACES = os.getenv("CODESPACES", "false").lower() == "true"
if not DEBUG and not IS_TESTING and SECRET_KEY == "unsafe-development-key":
    raise ImproperlyConfigured("Canlı ortamda DJANGO_SECRET_KEY zorunludur.")
if IS_CODESPACES:
    ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, ".app.github.dev"]))
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([*CSRF_TRUSTED_ORIGINS, "https://*.app.github.dev"]))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "apps.core",
    "apps.accounts",
    "apps.listings",
    "apps.managed_services",
    "apps.partners",
    "apps.support_center",
    "apps.ai_listing.apps.AIListingConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.listings.context_processors.notification_counts",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr-tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if IS_TESTING
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ilansehri-default",
    }
}

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "İlan Şehri <noreply@ilansehri.com>")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "core:home"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = not DEBUG and not IS_TESTING
CSRF_COOKIE_SECURE = not DEBUG and not IS_TESTING
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
