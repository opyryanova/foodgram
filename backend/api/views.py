# backend/api/views.py
from collections import defaultdict

from django.db.models import Exists, OuterRef, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from api.permissions import IsAuthorOrReadOnly  # добавим в следующем шаге
from api.serializers import (
    IngredientSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    RecipeWriteSerializer,
    SetUserAvatarSerializer,
    SubscriptionsSerializer,
    SubscribeAuthorSerializer,
    TagSerializer,
    UserInfoSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,   # имя through-модели — как в нашем serializers.py
    ShoppingCart,
    Subscription,
    Tag,
)
from users.models import User, Profile


# --------- TAGS ---------
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all().order_by('id')
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


# --------- INGREDIENTS ---------
class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Поиск по ?name= — регистронезависимый startswith, затем icontains.
    """
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    def get_queryset(self):
        qs = Ingredient.objects.all().order_by('name', 'measurement_unit')
        name = self.request.query_params.get('name')
        if name:
            name = name.strip()
            begins = qs.filter(name__istartswith=name)
            rest = qs.filter(name__icontains=name).exclude(pk__in=begins.values('pk'))
            return begins.union(rest)
        return qs


# --------- USERS (Djoser) ---------
class UserViewSet(DjoserUserViewSet):
    """
    Расширяем Djoser users:
    - GET /users/subscriptions/ — список авторов
    - POST/DELETE /users/{id}/subscribe/ — подписаться/отписаться
    - PUT/PATCH/DELETE /users/me/avatar/ — обновить/удалить аватар
    """
    serializer_class = UserInfoSerializer

    def get_queryset(self):
        return User.objects.all().order_by('id')

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        authors = User.objects.filter(
            subscriptions_author__user=request.user
        ).order_by('id').prefetch_related('recipes')
        page = self.paginate_queryset(authors)
        serializer = SubscriptionsSerializer(
            page or authors, many=True, context={'request': request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='subscribe')
    def subscribe(self, request, *args, **kwargs):
        """
        Не полагаемся на имя URL-параметра (id/pk) — берём автора через self.get_object().
        """
        author = self.get_object()

        if request.method.lower() == 'post':
            if author == request.user:
                return Response(
                    {'errors': 'Нельзя подписаться на себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            obj, created = Subscription.objects.get_or_create(
                user=request.user, author=author
            )
            if not created:
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            data = SubscribeAuthorSerializer(author, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        # DELETE
        deleted, _ = Subscription.objects.filter(
            user=request.user, author=author
        ).delete()
        if deleted == 0:
            return Response(
                {'errors': 'Подписки не было.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['put', 'patch', 'delete'],
            permission_classes=[IsAuthenticated], url_path='me/avatar')
    def set_avatar(self, request):
        """
        Работаем с моделью Profile, потому что аватар хранится там.
        PUT/PATCH — загрузка/замена, DELETE — удаление.
        """
        profile, _ = Profile.objects.get_or_create(user=request.user)

        if request.method == 'DELETE':
            if profile.avatar:
                profile.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = SetUserAvatarSerializer(
            profile, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            UserInfoSerializer(request.user, context={'request': request}).data,
            status=status.HTTP_200_OK
        )


# --------- RECIPES ----------
class RecipeViewSet(viewsets.ModelViewSet):
    """
    - Список/детально/создать/обновить/удалить рецепт
    - POST/DELETE /recipes/{id}/favorite/
    - POST/DELETE /recipes/{id}/shopping_cart/
    - GET /recipes/download_shopping_cart/ — агрегированный список покупок
    Поддержка фильтров: ?tags=slug1&tags=slug2&author=<id>&is_favorited=1&is_in_shopping_cart=1
    """
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    filter_backends = (DjangoFilterBackend,)

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None

        qs = Recipe.objects.all().select_related('author').prefetch_related(
            'tags',
            'recipe_ingredients__ingredient',  # related_name through-модели
        )

        # Предвычислим флаги для текущего пользователя
        if user:
            fav_exists = Favorite.objects.filter(user=user, recipe=OuterRef('pk'))
            cart_exists = ShoppingCart.objects.filter(user=user, recipe=OuterRef('pk'))
            qs = qs.annotate(
                is_favorited=Exists(fav_exists),
                is_in_shopping_cart=Exists(cart_exists),
            )

        # Фильтры по query params
        params = self.request.query_params

        author_id = params.get('author')
        if author_id:
            qs = qs.filter(author_id=author_id)

        tags = params.getlist('tags')
        if tags:
            qs = qs.filter(tags__slug__in=tags).distinct()

        def _truthy(v):
            return v in ('1', 'true', 'True', 'yes', 'on')

        if user and _truthy(params.get('is_favorited', '')):
            qs = qs.filter(favorites__user=user)

        if user and _truthy(params.get('is_in_shopping_cart', '')):
            qs = qs.filter(shoppingcarts__user=user)

        return qs.order_by('-id')

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # --- favorite ---
    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method.lower() == 'post':
            obj, created = Favorite.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            if not created:
                return Response(
                    {'errors': 'Уже в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            data = RecipeShortSerializer(recipe, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        # DELETE
        deleted, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if deleted == 0:
            return Response(
                {'errors': 'Этого рецепта нет в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- shopping_cart ---
    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method.lower() == 'post':
            obj, created = ShoppingCart.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            if not created:
                return Response(
                    {'errors': 'Уже в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            data = RecipeShortSerializer(recipe, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        # DELETE
        deleted, _ = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if deleted == 0:
            return Response(
                {'errors': 'Этого рецепта нет в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- download_shopping_cart ---
    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated], url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        """
        Агрегируем ингредиенты по всем рецептам из корзины текущего пользователя.
        Формат: "Название — сумма ЕИ".
        """
        items = RecipeIngredient.objects.filter(
            recipe__shoppingcarts__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total=Sum('amount')).order_by('ingredient__name')

        lines = []
        for it in items:
            name = it['ingredient__name']
            mu = it['ingredient__measurement_unit']
            total = it['total']
            lines.append(f"{name} — {total} {mu}")

        content = "\n".join(lines) if lines else "Список покупок пуст."
        response = HttpResponse(content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response
