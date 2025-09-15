from foodgram.settings import *
from pathlib import Path

BASE = Path(__file__).resolve().parent

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE / 'db.sqlite3'),
    }
}

DEBUG = True

MEDIA_ROOT = str(BASE / 'media')
STATIC_ROOT = str(BASE / 'static')
