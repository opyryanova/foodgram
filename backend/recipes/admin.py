from django.conf import settings
from django.contrib import admin, messages
from django.db.models import Count
from django.forms import TextInput
from django.urls import reverse
from django.utils.dates import MONTHS
from django.utils.html import format_html, format_html_join
from django.utils.http import urlencode
from rangefilter.filters import DateRangeFilter

from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShortLink,
    ShoppingCart,
    Subscription,
    Tag,
)

admin.site.site_header = "Foodgram — админка"
admin.site.site_title = "Foodgram | Администрирование"
admin.site.index_title = "Панель управления"
admin.site.site_url = getattr(settings, "FRONTEND_BASE_URL", "/")


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1
    autocomplete_fields = ("ingredient",)
    fields = ("ingredient", "amount")


class IngredientUsageInline(admin.TabularInline):
    model = RecipeIngredient
    fk_name = "ingredient"
    extra = 0
    autocomplete_fields = ("recipe",)
    fields = ("recipe", "amount")
    verbose_name = "Рецепт"
    verbose_name_plural = "Где используется"


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "measurement_unit", "recipes_count_link")
    search_fields = ("^name",)
    list_filter = ("measurement_unit",)
    ordering = ("name",)
    inlines = (IngredientUsageInline,)
    readonly_fields = ("recipes_list_link",)

    def _recipe_changelist_url(self, **params):
        app_label = Recipe._meta.app_label
        model_name = Recipe._meta.model_name
        base = reverse(f"admin:{app_label}_{model_name}_changelist")
        return f"{base}?{urlencode(params)}"

    @admin.display(description="Рецептов")
    def recipes_count_link(self, obj: Ingredient):
        count = (
            Recipe.objects.filter(recipe_ingredients__ingredient=obj)
            .distinct()
            .count()
        )
        url = self._recipe_changelist_url(ingredients__id__exact=obj.id)
        return format_html('<a href="{}">{}</a>', url, count)

    @admin.display(description="Все рецепты с этим ингредиентом")
    def recipes_list_link(self, obj: Ingredient):
        if not obj or not obj.pk:
            return "Появится после сохранения"
        url = self._recipe_changelist_url(ingredients__id__exact=obj.id)
        return format_html(
            '<a target="_blank" href="{}">Все рецепты →</a>',
            url,
        )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "color":
            kwargs["widget"] = TextInput(attrs={"type": "color"})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class CookingTimeFilter(admin.SimpleListFilter):
    title = "время готовки"
    parameter_name = "cooking_time_range"

    def lookups(self, request, model_admin):
        return (
            ("15", "≤ 15 мин"),
            ("30", "16–30 мин"),
            ("60", "31–60 мин"),
            ("61", "> 60 мин"),
        )

    def queryset(self, request, queryset):
        v = self.value()
        if v == "15":
            return queryset.filter(cooking_time__lte=15)
        if v == "30":
            return queryset.filter(
                cooking_time__gte=16,
                cooking_time__lte=30,
            )
        if v == "60":
            return queryset.filter(
                cooking_time__gte=31,
                cooking_time__lte=60,
            )
        if v == "61":
            return queryset.filter(cooking_time__gt=60)
        return queryset


class PubYearFilter(admin.SimpleListFilter):
    title = "год публикации"
    parameter_name = "pub_year"

    def lookups(self, request, model_admin):
        years = model_admin.model.objects.dates(
            "pub_date",
            "year",
            order="DESC"
        )
        return [(y.year, str(y.year)) for y in years]

    def queryset(self, request, queryset):
        v = self.value()
        if v and v.isdigit():
            return queryset.filter(pub_date__year=int(v))
        return queryset


class PubMonthFilter(admin.SimpleListFilter):
    title = "месяц публикации"
    parameter_name = "pub_month"

    def lookups(self, request, model_admin):
        year = request.GET.get("pub_year")
        if year and year.isdigit():
            months = (
                model_admin.model.objects.filter(pub_date__year=int(year))
                .dates("pub_date", "month", order="ASC")
            )
            return [
                (m.month, MONTHS.get(m.month, f"{m.month:02d}"))
                for m in months
            ]
        return [(i, MONTHS.get(i, f"{i:02d}")) for i in range(1, 13)]

    def queryset(self, request, queryset):
        v = self.value()
        if v and v.isdigit():
            qs = queryset.filter(pub_date__month=int(v))
            year = request.GET.get("pub_year")
            if year and year.isdigit():
                qs = qs.filter(pub_date__year=int(year))
            return qs
        return queryset


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "image_thumb",
        "name",
        "tags_list",
        "author_link",
        "favorites_count_link",
        "pub_date",
    )
    list_display_links = ("id", "name")
    search_fields = ("name", "author__username", "author__email")
    list_filter = (
        "tags",
        "author",
        CookingTimeFilter,
        PubYearFilter,
        PubMonthFilter,
        ("pub_date", DateRangeFilter),
        ("pub_date", admin.DateFieldListFilter),
    )
    inlines = (RecipeIngredientInline,)
    readonly_fields = ("pub_date", "image_preview", "recipes_by_author_link")
    ordering = ("-pub_date",)
    filter_horizontal = ("tags",)
    autocomplete_fields = ("author",)
    actions = ["make_shortlinks"]

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .select_related("author")
            .prefetch_related(
                "tags",
                "favorites",
                "shoppingcarts",
                "recipe_ingredients__ingredient",
            )
        )
        return qs.annotate(favorites_cnt=Count("favorites", distinct=True))

    @admin.display(description="Теги")
    def tags_list(self, obj: Recipe):
        tags = list(obj.tags.all())
        if not tags:
            return "—"
        app_label = Recipe._meta.app_label
        model_name = Recipe._meta.model_name
        base = reverse(f"admin:{app_label}_{model_name}_changelist")
        rows = [
            (base, urlencode({"tags__id__exact": t.id}), t.name)
            for t in tags
        ]
        return format_html_join(
            " ",
            (
                '<a href="{}?{}" '
                'style="display:inline-block;padding:1px 6px;'
                "margin:0 4px 4px 0;border:1px solid #ddd;"
                'border-radius:10px;text-decoration:none;">{}</a>'
            ),
            rows,
        )

    @admin.display(description="Фото")
    def image_thumb(self, obj):
        img = getattr(obj, "image", None)
        if not img:
            return "—"
        try:
            return format_html(
                (
                    '<img src="{}" '
                    'style="height:40px;width:auto;border-radius:4px;" />'
                ),
                img.url,
            )
        except Exception:
            return "—"

    @admin.display(description="Предпросмотр")
    def image_preview(self, obj):
        img = getattr(obj, "image", None)
        if not img:
            return "—"
        try:
            return format_html(
                (
                    '<img src="{}" '
                    'style="max-height:220px;width:auto;border:1px solid #ddd;'
                    'padding:2px;border-radius:6px;" />'
                ),
                img.url,
            )
        except Exception:
            return "—"

    @admin.display(description="В избранном", ordering="favorites_cnt")
    def favorites_count_link(self, obj):
        count = getattr(obj, "favorites_cnt", None)
        if count is None:
            count = obj.favorites.count()
        app_label = Favorite._meta.app_label
        model_name = Favorite._meta.model_name
        url = reverse(f"admin:{app_label}_{model_name}_changelist")
        query = urlencode({"recipe__id__exact": obj.id})
        return format_html('<a href="{}?{}">{}</a>', url, query, count)

    @admin.display(description="Автор", ordering="author__username")
    def author_link(self, obj):
        app_label = Recipe._meta.app_label
        model_name = Recipe._meta.model_name
        changelist_url = reverse(f"admin:{app_label}_{model_name}_changelist")
        query = urlencode({"author__id__exact": obj.author_id})
        return format_html(
            '<a href="{}?{}">{}</a>',
            changelist_url,
            query,
            obj.author,
        )

    @admin.display(description="Все рецепты этого автора")
    def recipes_by_author_link(self, obj):
        if not obj or not obj.pk:
            return "Появится после сохранения"
        app_label = Recipe._meta.app_label
        model_name = Recipe._meta.model_name
        changelist_url = reverse(f"admin:{app_label}_{model_name}_changelist")
        query = urlencode({"author__id__exact": obj.author_id})
        return format_html(
            '<a target="_blank" href="{}?{}">Все рецепты автора →</a>',
            changelist_url,
            query,
        )

    @admin.action(description="Создать/обновить короткую ссылку")
    def make_shortlinks(self, request, queryset):
        created = 0
        for recipe in queryset:
            _, was_created = ShortLink.objects.get_or_create(recipe=recipe)
            created += 1 if was_created else 0
        if created:
            self.message_user(
                request,
                f"Создано коротких ссылок: {created}",
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "Все выбранные рецепты уже имеют короткие ссылки.",
                level=messages.INFO,
            )


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
