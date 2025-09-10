# backend/core/views.py
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect

from recipes.models import ShortLink


def shortlink_redirect(request, code: str):
    """
    Редирект по короткой ссылке на страницу рецепта фронта.

    - Ищем ShortLink по коду.
    - Собираем целевой URL фронта: <FRONTEND_BASE_URL>/recipes/<id>/
      * Если в settings.FRONTEND_BASE_URL ничего не задано — используем http://localhost.
    - Делаем 302 Redirect.
    """
    sl = get_object_or_404(ShortLink, code=code)
    recipe_id = sl.recipe_id

    base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost").rstrip("/")
    target = f"{base}/recipes/{recipe_id}/"

    return redirect(target)
