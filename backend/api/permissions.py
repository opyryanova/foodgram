from typing import Any

from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request


def is_admin_user(user: Any) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and (
            getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        )
    )


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(
        self,
        request: Request,
        view: Any,
        obj: Any,
    ) -> bool:
        if request.method in SAFE_METHODS:
            return True

        user = getattr(request, "user", None)

        if is_admin_user(user):
            return True

        if not getattr(user, "is_authenticated", False):
            return False

        return getattr(obj, "author", None) == user


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(
        self,
        request: Request,
        view: Any,
        obj: Any,
    ) -> bool:
        if request.method in SAFE_METHODS:
            return True

        user = getattr(request, "user", None)

        if is_admin_user(user):
            return True

        if not getattr(user, "is_authenticated", False):
            return False

        return getattr(obj, "user", None) == user
