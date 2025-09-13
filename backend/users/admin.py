from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.html import format_html

from .models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    fk_name = "user"
    extra = 0
    can_delete = True


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline]

    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "date_joined",
    )
    list_display_links = ("id", "username")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
    )
    ordering = ("id",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "avatar_preview")
    list_display_links = ("id", "user")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    list_filter = ("avatar",)
    autocomplete_fields = ("user",)
    readonly_fields = ("avatar_preview",)

    fieldsets = ((None, {"fields": ("user", "avatar", "avatar_preview")}),)

    @admin.display(description="Аватар")
    def avatar_preview(self, obj):
        img = getattr(obj, "avatar", None)
        if img:
            return format_html(
                (
                    '<img src="{}" style="height:40px;width:40px;'
                    "object-fit:cover;border-radius:50%;"
                    '">'
                ),
                img.url,
            )
        return "—"
