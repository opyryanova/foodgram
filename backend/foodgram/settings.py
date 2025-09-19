import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    parts = raw.replace(",", " ").split()
    return [chunk.strip() for chunk in parts if chunk.strip()]


SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes", "y")

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    "127.0.0.1 localhost foodgram-practicum.hopto.org",
)
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    (
        "http://127.0.0.1 http://localhost "
        "http://foodgram-practicum.hopto.org "
        "https://foodgram-practicum.hopto.org"
    ),
)

APPEND_SLASH = os.getenv("APPEND_SLASH", "true").lower() in (
    "1",
    "true",
    "yes",
    "y",
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "djoser",
    "rangefilter",
    "api.apps.ApiConfig",
    "recipes",
    "users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.foodgram.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "foodgram.wsgi.application"

if os.getenv("DB_ENGINE"):
    DATABASES = {
        "default": {
            "ENGINE": os.getenv(
                "DB_ENGINE",
                "django.db.backends.postgresql",
            ),
            "NAME": os.getenv("DB_NAME", "foodgram"),
            "USER": os.getenv("POSTGRES_USER", "foodgram"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "foodgram"),
            "HOST": os.getenv("DB_HOST", "db"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = os.getenv("TIME_ZONE", "Europe/Moscow")
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATIC_ROOT = os.getenv("STATIC_ROOT", os.path.join(BASE_DIR, "static"))
# MEDIA_ROOT = os.getenv("MEDIA_ROOT", os.path.join(BASE_DIR, "media"))
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "api.pagination.DefaultPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}

if (
    os.getenv("DISABLE_BROWSABLE_API", "true").lower()
    in ("1", "true", "yes", "y")
    and not DEBUG
):
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
    ]

DJOSER = {
    "LOGIN_FIELD": "email",
    "USER_ID_FIELD": "id",
    "HIDE_USERS": False,
    "SERIALIZERS": {
        "token_create": "api.serializers.LoginOrEmailTokenCreateSerializer",
        "user": "api.serializers.UserInfoSerializer",
        "current_user": "api.serializers.UserInfoSerializer",
        "user_create": "api.serializers.UserCreateSerializer",
    },
}

AUTH_USER_MODEL = os.getenv("AUTH_USER_MODEL", "users.User")

if os.getenv(
    "USE_X_FORWARDED_PROTO",
    "true"
).lower() in ("1", "true", "yes", "y"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

USE_X_FORWARDED_HOST = os.getenv(
    "USE_X_FORWARDED_HOST",
    "true",
).lower() in ("1", "true", "yes", "y")

SECURE_SSL_REDIRECT = os.getenv(
    "SECURE_SSL_REDIRECT",
    "false" if DEBUG else "true",
).lower() in ("1", "true", "yes", "y")

SESSION_COOKIE_SECURE = os.getenv(
    "SESSION_COOKIE_SECURE",
    "false" if DEBUG else "true",
).lower() in ("1", "true", "yes", "y")

CSRF_COOKIE_SECURE = os.getenv(
    "CSRF_COOKIE_SECURE",
    "false" if DEBUG else "true",
).lower() in ("1", "true", "yes", "y")

SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {message}", "style": "{"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"}
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if not DEBUG else "DEBUG",
    },
}

DATA_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv("DATA_UPLOAD_MAX_MEMORY_SIZE", str(25 * 1024 * 1024))
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
