# backend/recipes/admin.py
from django.contrib import admin

from .models import (
    Tag,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
    Subscription,
    ShortLink,
)


class RecipeIngredientInline(admin.TabularInline):
    """Инлайн для ингредиентов внутри рецепта."""
    model = RecipeIngredient
    extra = 0
    autocomplete_fields = ("ingredient",)
    min_num = 0


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)
    ordering = ("name",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "author",
        "servings",       # ← видно прямо в списке
        "cooking_time",
        "favorites_count",
        "pub_date",
    )
    list_filter = ("tags", "author")
    search_fields = ("name", "author__username", "author__first_name", "author__last_name")
    readonly_fields = ("pub_date", "favorites_count")
    inlines = (RecipeIngredientInline,)
    filter_horizontal = ("tags",)
    autocomplete_fields = ("author",)

    fieldsets = (
        (None, {"fields": ("author", "name", "image", "text")}),
        ("Параметры", {"fields": ("cooking_time", "servings")}),  # ← редактируемое поле
        ("Теги", {"fields": ("tags",)}),
        ("Служебное", {"fields": ("favorites_count", "pub_date")}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # чуть оптимизации для списка
        return qs.select_related("author").prefetch_related("tags", "favorited_by")

    @admin.display(description="В избранном")
    def favorites_count(self, obj):
        return obj.favorited_by.count()


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    search_fields = ("user__username", "recipe__name")
    autocomplete_fields = ("user", "recipe")


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    search_fields = ("user__username", "recipe__name")
    autocomplete_fields = ("user", "recipe")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "author")
    search_fields = ("user__username", "author__username")
    autocomplete_fields = ("user", "author")


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ("code", "recipe")
    search_fields = ("code", "recipe__name")
    autocomplete_fields = ("recipe",)
