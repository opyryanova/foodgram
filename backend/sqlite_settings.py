# локальные настройки для разработки на SQLite
# отключаем претензии flake8 к звездочному импорту базовых настроек
from foodgram.settings import *  # noqa: F403,F401

from pathlib import Path

BASE = Path(__file__).resolve().parent

# База данных: SQLite в файле рядом с настройками
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE / "db.sqlite3"),
    }
}

# Режим разработки
DEBUG = True

# Разрешаем локальные хосты
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Доверяем локальные http-источники для csrf
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

# Важно: отключаем редирект на https на локали
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Статика и медиа локально (чтобы Django мог их складывать)
MEDIA_ROOT = str(BASE / "media")
STATIC_ROOT = str(BASE / "static")
