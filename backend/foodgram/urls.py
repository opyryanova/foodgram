# backend/foodgram/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from core.views import shortlink_redirect  # редирект по короткой ссылке

# Куда редиректить с корня сайта
FRONT_BASE = getattr(settings, "FRONTEND_BASE_URL", "http://localhost").rstrip("/")

urlpatterns = [
    # Редирект корня бэкенда на фронт (чтобы не видеть 404 при заходе на /)
    path("", RedirectView.as_view(url=f"{FRONT_BASE}/", permanent=False), name="front-root"),

    # Короткие ссылки: поддерживаем и со слешем, и без
    path("s/<str:code>/", shortlink_redirect, name="shortlink"),
    path("s/<str:code>", shortlink_redirect),

    path("admin/", admin.site.urls),
    path("api/auth/", include("djoser.urls")),
    path("api/auth/", include("djoser.urls.authtoken")),
    path("api/", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
