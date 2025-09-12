# backend/foodgram/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# Редиректы коротких ссылок /s/<code>
from api.views import ShortLinkRedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # --- КОРОТКИЕ ССЫЛКИ ---
    # Оба варианта, чтобы не зависеть от APPEND_SLASH и поведения прокси
    path("s/<str:code>/", ShortLinkRedirectView.as_view(), name="shortlink"),
    path("s/<str:code>", ShortLinkRedirectView.as_view()),

    # --- АУТЕНТИФИКАЦИЯ (DJOSER) ---
    # Логин по email ИЛИ username доступен на стандартном эндпоинте:
    # POST /api/auth/token/login/  (DRF Token), см. DJOSER['SERIALIZERS']['token_create']
    path("api/auth/", include("djoser.urls")),
    path("api/auth/", include("djoser.urls.authtoken")),

    # --- ОСНОВНОЙ API ---
    path("api/", include("api.urls")),
]

# В DEV режиме раздаем статику и медиа через Django.
# В проде это делает nginx (см. infra/nginx.conf).
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
