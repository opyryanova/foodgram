# backend/api/permissions.py
"""Кастомные пермишены проекта.

- IsAuthorOrReadOnly: читать могут все; изменять/удалять — автор объекта или админ.
- IsOwnerOrAdmin:    читать могут все; изменять/удалять — владелец (obj.user) или админ.

Использование:
    class RecipeViewSet(ModelViewSet):
        permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    class FavoriteViewSet(ModelViewSet):
        permission_classes = (IsAuthenticated, IsOwnerOrAdmin)
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request


def is_admin_user(user: Any) -> bool:
    """Единая проверка административных привилегий (staff или superuser)."""
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
    )


class IsAuthorOrReadOnly(BasePermission):
    """
    Доступ к объектам с полем `author` (например, Recipe):
      - безопасные методы (GET, HEAD, OPTIONS) доступны всем;
      - PATCH/PUT/DELETE может автор объекта;
      - администратор/суперпользователь имеют полный доступ.
    """

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:  # type: ignore[override]
        # Чтение разрешено всем
        if request.method in SAFE_METHODS:
            return True

        user = getattr(request, "user", None)

        # Админ всегда может
        if is_admin_user(user):
            return True

        # Остальные — только автор
        if not getattr(user, "is_authenticated", False):
            return False

        return getattr(obj, "author", None) == user


class IsOwnerOrAdmin(BasePermission):
    """
    Доступ к объектам, принадлежащим пользователю (поле `user`):
      - безопасные методы (GET, HEAD, OPTIONS) доступны всем;
      - PATCH/PUT/DELETE может владелец (`obj.user == request.user`);
      - администратор/суперпользователь имеют полный доступ.

    Подходит для моделей Favorite, ShoppingCart, Subscription, Profile и т.п.
    """

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:  # type: ignore[override]
        # Чтение разрешено всем
        if request.method in SAFE_METHODS:
            return True

        user = getattr(request, "user", None)

        # Админ всегда может
        if is_admin_user(user):
            return True

        # Остальные — только владелец
        if not getattr(user, "is_authenticated", False):
            return False

        return getattr(obj, "user", None) == user
