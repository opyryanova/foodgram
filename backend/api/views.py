from __future__ import annotations

import base64
from typing import Optional

from django.db.models import (
    Exists, OuterRef, Sum, F, Value,
    FloatField, IntegerField, ExpressionWrapper,
)
from django.db.models.functions import Coalesce, Ceil, Cast
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
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
    RecipeIngredient,
    ShoppingCart,
    Subscription,
    Tag,
)
from users.models import Profile, User


# --------- TAGS ---------
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all().order_by("id")
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


# --------- INGREDIENTS ---------
class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Поиск по ?name= выполняет IngredientFilter: сначала istartswith, затем icontains.
    Если ?name= не передан — сортируем алфавитно; если передан — отдаём
    управление сортировкой фильтру (не задаём order_by в queryset).
    """
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter

    def get_queryset(self):
        qs = Ingredient.objects.all()
        # Ключевая правка: не навязываем order_by, когда есть ?name=
        if self.request and self.request.query_params.get("name"):
            return qs
        return qs.order_by("name", "measurement_unit")


# --------- USERS (Djoser) ---------
class UserViewSet(DjoserUserViewSet):
    """
    Расширение Djoser users:
    - GET  /users/subscriptions/           — список авторов
    - POST/DELETE /users/{id}/subscribe/   — подписаться/отписаться
    - PUT/PATCH/DELETE /users/me/avatar/   — обновить/удалить аватар
    """
    serializer_class = UserInfoSerializer

    def get_queryset(self):
        return User.objects.all().order_by("id")

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        authors = (
            User.objects
            .filter(followers__user=request.user)
            .order_by("id")
            .prefetch_related("recipes")
        )
        page = self.paginate_queryset(authors)
        serializer = SubscriptionsSerializer(page or authors, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated], url_path="subscribe")
    def subscribe(self, request, *args, **kwargs):
        author = self.get_object()

        if request.method.lower() == "post":
            if author == request.user:
                return Response({"errors": "Нельзя подписаться на себя."}, status=status.HTTP_400_BAD_REQUEST)
            obj, created = Subscription.objects.get_or_create(user=request.user, author=author)
            if not created:
                return Response({"errors": "Вы уже подписаны на этого пользователя."}, status=status.HTTP_400_BAD_REQUEST)
            data = SubscribeAuthorSerializer(author, context={"request": request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = Subscription.objects.filter(user=request.user, author=author).delete()
        if deleted == 0:
            return Response({"errors": "Подписки не было."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["put", "patch", "delete"], permission_classes=[IsAuthenticated], url_path="me/avatar")
    def set_avatar(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)

        if request.method == "DELETE":
            if profile.avatar:
                profile.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = SetUserAvatarSerializer(profile, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserInfoSerializer(request.user, context={"request": request}).data, status=status.HTTP_200_OK)


# --------- RECIPES ----------
class RecipeViewSet(viewsets.ModelViewSet):
    """
    - Список/детально/создать/обновить/удалить рецепт
    - POST/PATCH/DELETE /recipes/{id}/shopping_cart/
    - POST/DELETE         /recipes/{id}/favorite/
    - GET                 /recipes/download_shopping_cart/
    Фильтры: ?tags=&author=&is_favorited=&is_in_shopping_cart=&name=
    """
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None

        qs = (
            Recipe.objects
            .all()
            .select_related("author")
            .prefetch_related("tags", "recipe_ingredients__ingredient")
        )

        if user:
            fav_exists = Favorite.objects.filter(user=user, recipe=OuterRef("pk"))
            cart_exists = ShoppingCart.objects.filter(user=user, recipe=OuterRef("pk"))
            qs = qs.annotate(
                is_favorited=Exists(fav_exists),
                is_in_shopping_cart=Exists(cart_exists),
            )

        return qs.order_by("-id")

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RecipeSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method.lower() == "post":
            obj, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)
            if not created:
                return Response({"errors": "Уже в избранном."}, status=status.HTTP_400_BAD_REQUEST)
            data = RecipeShortSerializer(recipe, context={"request": request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = Favorite.objects.filter(user=request.user, recipe=recipe).delete()
        if deleted == 0:
            return Response({"errors": "Этого рецепта нет в избранном."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post", "patch", "delete"], permission_classes=[IsAuthenticated], url_path="shopping_cart")
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        def _parse_servings(raw):
            if raw is None or raw == "":
                return None
            try:
                val = int(raw)
                if val < 1:
                    raise ValueError
                return val
            except (TypeError, ValueError):
                return "error"

        method = request.method.lower()

        if method == "post":
            servings = _parse_servings(request.data.get("servings"))
            if servings == "error":
                return Response({"errors": "servings должен быть положительным целым числом."}, status=status.HTTP_400_BAD_REQUEST)
            obj, created = ShoppingCart.objects.get_or_create(user=request.user, recipe=recipe)
            if not created:
                return Response({"errors": "Уже в списке покупок."}, status=status.HTTP_400_BAD_REQUEST)
            if servings is not None:
                obj.servings = servings
                obj.save(update_fields=["servings"])
            data = RecipeShortSerializer(recipe, context={"request": request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        if method == "patch":
            obj = ShoppingCart.objects.filter(user=request.user, recipe=recipe).first()
            if not obj:
                return Response({"errors": "Этого рецепта нет в списке покупок."}, status=status.HTTP_400_BAD_REQUEST)
            servings = _parse_servings(request.data.get("servings"))
            if servings in (None, "error"):
                return Response({"errors": "Укажите корректный servings (целое >= 1)."}, status=status.HTTP_400_BAD_REQUEST)
            obj.servings = servings
            obj.save(update_fields=["servings"])
            data = RecipeShortSerializer(recipe, context={"request": request}).data
            return Response(data, status=status.HTTP_200_OK)

        deleted, _ = ShoppingCart.objects.filter(user=request.user, recipe=recipe).delete()
        if deleted == 0:
            return Response({"errors": "Этого рецепта нет в списке покупок."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="download_shopping_cart")
    def download_shopping_cart(self, request):
        scale = ExpressionWrapper(
            Value(1.0) * Coalesce(F("recipe__shoppingcarts__servings"), F("recipe__servings")) / F("recipe__servings"),
            output_field=FloatField(),
        )
        amount_scaled = ExpressionWrapper(F("amount") * scale, output_field=FloatField())

        items = (
            RecipeIngredient.objects
            .filter(recipe__shoppingcarts__user=request.user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total=Cast(Ceil(Sum(amount_scaled)), IntegerField()))
            .order_by("ingredient__name")
        )

        lines = [f"{it['ingredient__name']} — {it['total']} {it['ingredient__measurement_unit']}" for it in items]
        content = "\n".join(lines) if lines else "Список покупок пуст."
        response = HttpResponse(content, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="shopping_list.txt"'
        return response


# --------- SHORT LINKS (редирект /s/<code>) ----------

_BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _decode_base62(s: str) -> Optional[int]:
    try:
        n = 0
        for ch in s:
            n = n * 62 + _BASE62_ALPHABET.index(ch)
        return n
    except ValueError:
        return None


def _decode_urlsafe_b64_to_int(s: str) -> Optional[int]:
    try:
        pad = "=" * (-len(s) % 4)
        raw = base64.urlsafe_b64decode(s + pad)
        txt = raw.decode("utf-8", errors="ignore")
        if txt.isdigit():
            return int(txt)
        digits = "".join(ch for ch in txt if ch.isdigit())
        return int(digits) if digits else None
    except Exception:
        return None


def _lookup_direct_url(code: str) -> Optional[str]:
    try:
        from recipes.models import ShortLink  # type: ignore
        obj = ShortLink.objects.filter(code=code).first()
        if obj and getattr(obj, "target_url", None):
            return str(obj.target_url)
    except Exception:
        pass
    return None


def _lookup_recipe_id(code: str) -> Optional[int]:
    try:
        from recipes.models import ShortLink  # type: ignore
        obj = ShortLink.objects.select_related("recipe").filter(code=code).only("recipe_id").first()
        if obj and obj.recipe_id:
            return int(obj.recipe_id)
    except Exception:
        pass
    return None


def _recipe_exists(pk: int) -> bool:
    return Recipe.objects.filter(pk=pk).only("id").exists()


def _resolve_recipe_id(code: str) -> Optional[int]:
    rid = _lookup_recipe_id(code)
    if rid:
        return rid

    if code.isdigit():
        rid = int(code)
        return rid if _recipe_exists(rid) else None

    try:
        rid = int(code, 36)
        if _recipe_exists(rid):
            return rid
    except ValueError:
        pass

    def _decode_base62_local(s: str) -> Optional[int]:
        try:
            n = 0
            for ch in s:
                n = n * 62 + _BASE62_ALPHABET.index(ch)
            return n
        except ValueError:
            return None

    rid = _decode_base62_local(code)
    if rid and _recipe_exists(rid):
        return rid

    try:
        pad = "=" * (-len(code) % 4)
        raw = base64.urlsafe_b64decode(code + pad)
        txt = raw.decode("utf-8", errors="ignore")
        if txt.isdigit():
            rid = int(txt)
        else:
            digits = "".join(ch for ch in txt if ch.isdigit())
            rid = int(digits) if digits else None
        if rid and _recipe_exists(rid):
            return rid
    except Exception:
        pass

    return None


class ShortLinkRedirectView(View):
    FRONT_RECIPE_PATH = "/recipes/{id}"

    def get(self, request, code: str, *args, **kwargs):
        code = (code or "").strip()
        if not code:
            return redirect("/", permanent=False)

        direct = _lookup_direct_url(code)
        if direct:
            return redirect(direct, permanent=False)

        rid = _resolve_recipe_id(code)
        if rid:
            return redirect(self.FRONT_RECIPE_PATH.format(id=rid), permanent=False)

        return redirect("/", permanent=False)
