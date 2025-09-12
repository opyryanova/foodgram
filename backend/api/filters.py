# backend/api/filters.py
"""
Наборы фильтров для DRF (django-filter).

Подключение в вьюсетах:
    from django_filters.rest_framework import DjangoFilterBackend
    from api.filters import RecipeFilter, IngredientFilter

    class RecipeViewSet(ModelViewSet):
        filter_backends = (DjangoFilterBackend,)
        filterset_class = RecipeFilter

    class IngredientViewSet(ReadOnlyModelViewSet):
        filter_backends = (DjangoFilterBackend,)
        filterset_class = IngredientFilter
"""

from __future__ import annotations

import django_filters
from django.db.models import Exists, OuterRef, QuerySet

from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag


# ---------- RecipeFilter ----------

class RecipeFilter(django_filters.FilterSet):
    """
    Фильтр для рецептов.

    Параметры запроса:
      - tags: повторяемый параметр со slug тегов
               ?tags=breakfast&tags=dinner
      - author: id автора (int)
               ?author=12
      - is_favorited: 1/true/True/yes/on — только рецепты в избранном у текущего пользователя
               ?is_favorited=1
      - is_in_shopping_cart: 1/true/True/yes/on — только рецепты из корзины текущего пользователя
               ?is_in_shopping_cart=1
      - name: подстрочный поиск по названию (case-insensitive)
               ?name=борщ
    """

    # Несколько тегов по slug: ?tags=breakfast&tags=dinner
    # Делаем через method, чтобы гарантировать .distinct() при множественных джоинах.
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name="tags__slug",
        to_field_name="slug",
        queryset=Tag.objects.all(),
        method="filter_tags",
    )

    # Автор по id: ?author=1
    author = django_filters.NumberFilter(field_name="author__id")

    # Подстрочный поиск по названию: ?name=pie
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    # Булевы флаги через кастомные методы (зависят от request.user)
    is_favorited = django_filters.BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = django_filters.BooleanFilter(method="filter_is_in_shopping_cart")

    class Meta:
        model = Recipe
        fields = ("tags", "author", "name", "is_favorited", "is_in_shopping_cart")

    # --- вспомогательное ---

    @staticmethod
    def _truthy(value) -> bool:
        """Интерпретация truthy/falsey из строковых значений."""
        return str(value) in {"1", "true", "True", "yes", "on"}

    # --- методы фильтрации ---

    def filter_tags(self, queryset: QuerySet, name: str, values) -> QuerySet:
        """
        Фильтр по нескольким slug тегов с гарантированным distinct().
        """
        if not values:
            return queryset
        return queryset.filter(tags__slug__in=list(values)).distinct()

    def filter_is_favorited(self, queryset: QuerySet, name: str, value) -> QuerySet:
        """
        Оставить рецепты, которые текущий пользователь добавил в избранное.
        Если пользователь анонимен или value не truthy — без изменений.
        """
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not self._truthy(value):
            return queryset

        fav_exists = Favorite.objects.filter(user=user, recipe=OuterRef("pk"))
        return queryset.annotate(is_favorited=Exists(fav_exists)).filter(is_favorited=True)

    def filter_is_in_shopping_cart(self, queryset: QuerySet, name: str, value) -> QuerySet:
        """
        Оставить рецепты, которые текущий пользователь добавил в корзину.
        Если пользователь анонимен или value не truthy — без изменений.
        """
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not self._truthy(value):
            return queryset

        in_cart_exists = ShoppingCart.objects.filter(user=user, recipe=OuterRef("pk"))
        return queryset.annotate(is_in_cart=Exists(in_cart_exists)).filter(is_in_cart=True)


# ---------- IngredientFilter ----------

class IngredientFilter(django_filters.FilterSet):
    """
    Поиск ингредиентов по параметру ?name=
    Поведение:
      - сначала case-insensitive startswith;
      - затем остальные, где name icontains, без дублей;
      - итог объединяется, чтобы startswith шли первыми.
    """
    name = django_filters.CharFilter(method="filter_name")

    class Meta:
        model = Ingredient
        fields = ("name",)

    def filter_name(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        if not value:
            return queryset.order_by("name", "measurement_unit")
        needle = str(value).strip()
        begins = queryset.filter(name__istartswith=needle)
        rest = queryset.filter(name__icontains=needle).exclude(pk__in=begins.values("pk"))
        # union() теряет ordering, поэтому используем | и затем order_by
        combined = begins | rest
        return combined.order_by("name", "measurement_unit")
