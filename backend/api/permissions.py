# backend/api/permissions.py
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnly(BasePermission):
    """
    Доступы к объектам:
    - читать (GET, HEAD, OPTIONS) могут все пользователи;
    - изменять или удалять может только автор объекта;
    - суперпользователь и администратор всегда имеют полный доступ.
    """

    def has_object_permission(self, request, view, obj):
        # Любые безопасные методы (чтение) разрешены всем
        if request.method in SAFE_METHODS:
            return True

        user = request.user

        # Администратор и суперпользователь имеют полный доступ
        if user and (user.is_staff or user.is_superuser):
            return True

        # Проверяем автора у объекта (если есть поле author)
        author = getattr(obj, "author", None)
        return author == user
