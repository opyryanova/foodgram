from django.db.models import Case, IntegerField, QuerySet, Value, When
from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe, Tag


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(
        method='filter_is_favorited', label='В избранном'
    )
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart', label='В корзине покупок'
    )
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        method='filter_tags',
        label='Теги рецепта',
    )
    author = filters.NumberFilter(field_name='author__id', label='Автор')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'author',
            'name',
            'is_favorited',
            'is_in_shopping_cart'
        )

    def filter_tags(self, queryset: QuerySet, name: str, values) -> QuerySet:
        if not values:
            return queryset
        try:
            tag_ids = list(values.values_list('id', flat=True))
            return queryset.filter(tags__id__in=tag_ids).distinct()
        except Exception:
            slugs = [getattr(v, 'slug', v) for v in values]
            return queryset.filter(tags__slug__in=slugs).distinct()

    def filter_is_favorited(
            self,
            queryset: QuerySet,
            name: str,
            value
    ) -> QuerySet:
        user = getattr(getattr(self, 'request', None), 'user', None)
        if value and user and user.is_authenticated:
            return queryset.filter(favorites__user=user).distinct()
        return queryset

    def filter_is_in_shopping_cart(
            self,
            queryset: QuerySet,
            name: str, value
    ) -> QuerySet:
        user = getattr(getattr(self, 'request', None), 'user', None)
        if value and user and user.is_authenticated:
            return queryset.filter(shopping_recipe__user=user).distinct()
        return queryset


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(method='filter_name')

    class Meta:
        model = Ingredient
        fields = ('name',)

    def filter_name(
            self,
            queryset: QuerySet,
            name: str,
            value: str
    ) -> QuerySet:
        if not value:
            return queryset.order_by('name', 'measurement_unit')
        needle = str(value).strip()
        return (
            queryset.filter(name__icontains=needle)
            .annotate(
                __starts=Case(
                    When(name__istartswith=needle, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by('__starts', 'name', 'measurement_unit')
        )
