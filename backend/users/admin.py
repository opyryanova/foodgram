# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.html import format_html

from .models import User, Profile


class ProfileInline(admin.StackedInline):
    """Профиль как инлайн на странице пользователя."""
    model = Profile
    fk_name = "user"
    extra = 0
    can_delete = True


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Админка для пользователя.
    Регистрируем, чтобы работали autocomplete_fields в других админках.
    Плюс показываем базовые поля и добавляем инлайн профиля.
    """
    inlines = [ProfileInline]

    # что показывать в списке
    list_display = ("id", "username", "email", "first_name", "last_name", "is_staff", "date_joined")
    list_display_links = ("id", "username")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("id",)

    # автодополнение будет работать по username/email
    autocomplete_fields: tuple = ()


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Отдельная админка профиля (удобно смотреть/фильтровать аватары)."""
    list_display = ("id", "user", "avatar_preview")
    list_display_links = ("id", "user")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)

    fieldsets = (
        (None, {"fields": ("user", "avatar")}),
    )

    readonly_fields = ("avatar_preview",)

    def avatar_preview(self, obj):
        if getattr(obj, "avatar", None):
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:50%;">',
                obj.avatar.url,
            )
        return "—"

    avatar_preview.short_description = "Аватар"
