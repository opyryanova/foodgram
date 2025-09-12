from django.contrib import admin
from django.db.models import Count

from .models import (
    Tag, Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart, Subscription, ShortLink
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    ordering = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)
    ordering = ("name",)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1
    autocomplete_fields = ("ingredient",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "author", "favorites_count", "pub_date")
    search_fields = ("name", "author__username", "author__email")
    list_filter = ("tags", "author")
    inlines = (RecipeIngredientInline,)
    readonly_fields = ("pub_date",)
    ordering = ("-pub_date",)

    def get_queryset(self, request):
        qs = (super().get_queryset(request)
              .select_related("author")
              .prefetch_related(
                  "tags",
                  "favorites",
                  "shoppingcarts",
                  "recipe_ingredients__ingredient",
              ))
        return qs.annotate(favorites_cnt=Count("favorites", distinct=True))

    @admin.display(description="В избранном")
    def favorites_count(self, obj):
        return getattr(obj, "favorites_cnt", obj.favorites.count())


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user",)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    search_fields = ("user__username", "recipe__name")
    list_filter = ("user",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "author")
    search_fields = ("user__username", "author__username")
    list_filter = ("user", "author")


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "code")
    search_fields = ("code", "recipe__name")
    list_filter = ("recipe",)
