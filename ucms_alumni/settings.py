"""
Django settings for ucms_alumni project (DigitalOcean App Platform friendly).
Reads all secrets from environment variables—no .env file required in production.
"""

from pathlib import Path
import os
import dj_database_url

# ---------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv("DEBUG", "False") == "True"
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-prod")
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,ucmsalumni.com,www.ucmsalumni.com"
).split(",")

# App Platform / reverse proxy headers
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Static files middleware helper
    "whitenoise.runserver_nostatic",

    # your app(s)
    "alumni",
]

# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # keep directly after SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ucms_alumni.urls"

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

WSGI_APPLICATION = "ucms_alumni.wsgi.application"

# ---------------------------------------------------------------------
# Database (use DO Managed Postgres via DATABASE_URL; SQLite locally)
# ---------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

# ---------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Keep if you have a local /static folder (safe to leave)
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise: hashed, compressed static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------
# Auth / Sessions
# ---------------------------------------------------------------------
LOGIN_URL = "/login/"
LOGOUT_REDIRECT_URL = "/login/"
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "3600"))  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.getenv("SESSION_EXPIRE_AT_BROWSER_CLOSE", "True") == "True"

# ---------------------------------------------------------------------
# Security (enabled when DEBUG=False)
# ---------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS (enable once you're sure HTTPS works)
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------
# CSRF Trusted Origins (App Platform + your domain)
# Note: Must include scheme.
# ---------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = list(filter(None, [
    "https://*.ondigitalocean.app",
    "https://ucmsalumni.com",
    "https://www.ucmsalumni.com",
    os.getenv("EXTRA_CSRF_ORIGIN", "").strip(),  # optional extra, comma-splitting is not needed here
]))

# ---------------------------------------------------------------------
# Email (fill these as env vars in App Platform)
# ---------------------------------------------------------------------
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "hello@ucmsalumni.com")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"

# ---------------------------------------------------------------------
# App constants / OTP
# ---------------------------------------------------------------------
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))

# ---------------------------------------------------------------------
# Third-party API keys (set these in App Platform → Encrypted)
# ---------------------------------------------------------------------
THIRDPARTY_A_API_KEY = os.getenv("THIRDPARTY_A_API_KEY", "")
THIRDPARTY_B_API_KEY = os.getenv("THIRDPARTY_B_API_KEY", "")

# ---------------------------------------------------------------------
# Logging (send everything to console for App Platform logs)
# ---------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": True},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
