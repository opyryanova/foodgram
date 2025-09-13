import base64
from typing import Optional

from django.db.models import (
    Exists,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Sum,
    Value,
)
from django.db.models.functions import Cast, Ceil, Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from api.constants import BASE62_ALPHABET
from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    IngredientSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    RecipeWriteSerializer,
    SetUserAvatarSerializer,
    SubscribeAuthorSerializer,
    SubscriptionsSerializer,
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


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all().order_by("id")
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter

    def get_queryset(self):
        qs = Ingredient.objects.all()
        if self.request and self.request.query_params.get("name"):
            return qs
        return qs.order_by("name", "measurement_unit")


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all().order_by("id")

    def get_permissions(self):
        if self.action in (
            "me",
            "set_password",
            "set_username",
            "set_avatar",
            "subscriptions",
            "subscribe",
        ):
            return [IsAuthenticated()]
        if self.action in ("list", "retrieve", "create"):
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return UserInfoSerializer
        if self.action == "subscriptions":
            return SubscriptionsSerializer
        if self.action == "subscribe":
            return SubscribeAuthorSerializer
        if self.action == "set_avatar":
            return SetUserAvatarSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request):
        authors = User.objects.filter(followers__user=request.user).order_by(
            "id"
        )
        page = self.paginate_queryset(authors)
        serializer = self.get_serializer(
            page or authors,
            many=True,
            context={"request": request},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="subscribe",
    )
    def subscribe(self, request, *args, **kwargs):
        author = self.get_object()
        if request.method.lower() == "post":
            if author == request.user:
                return Response(
                    {"errors": "Нельзя подписаться на себя."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            obj, created = Subscription.objects.get_or_create(
                user=request.user,
                author=author,
            )
            if not created:
                return Response(
                    {
                        "errors": (
                            "Вы уже подписаны на этого пользователя."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data = SubscribeAuthorSerializer(
                author,
                context={"request": request},
            ).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = Subscription.objects.filter(
            user=request.user,
            author=author,
        ).delete()
        if deleted == 0:
            return Response(
                {"errors": "Подписки не было."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["put", "patch", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
    )
    def set_avatar(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)

        if request.method == "DELETE":
            if profile.avatar:
                profile.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = self.get_serializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_queryset(self):
        user = (
            self.request.user
            if self.request.user.is_authenticated
            else None
        )
        qs = (
            Recipe.objects.all()
            .select_related("author")
            .prefetch_related("tags", "recipe_ingredients__ingredient")
        )
        if user:
            fav_exists = Favorite.objects.filter(
                user=user,
                recipe=OuterRef("pk"),
            )
            cart_exists = ShoppingCart.objects.filter(
                user=user,
                recipe=OuterRef("pk"),
            )
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

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="favorite",
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        method = request.method.lower()

        if method == "post":
            obj, created = Favorite.objects.get_or_create(
                user=request.user,
                recipe=recipe,
            )
            if not created:
                return Response(
                    {"errors": "Уже в избранном."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data = RecipeShortSerializer(
                recipe,
                context={"request": request},
            ).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = Favorite.objects.filter(
            user=request.user,
            recipe=recipe,
        ).delete()
        if deleted == 0:
            return Response(
                {"errors": "Этого рецепта нет в избранном."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "patch", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="shopping_cart",
    )
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
                return Response(
                    {
                        "errors": (
                            "Поле servings должно быть положительным "
                            "целым числом."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            obj, created = ShoppingCart.objects.get_or_create(
                user=request.user,
                recipe=recipe,
            )
            if not created:
                return Response(
                    {"errors": "Уже в списке покупок."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if servings is not None:
                obj.servings = servings
                obj.save(update_fields=["servings"])
            data = RecipeShortSerializer(
                recipe,
                context={"request": request},
            ).data
            return Response(data, status=status.HTTP_201_CREATED)

        if method == "patch":
            obj = ShoppingCart.objects.filter(
                user=request.user,
                recipe=recipe,
            ).first()
            if not obj:
                return Response(
                    {"errors": "Этого рецепта нет в списке покупок."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            servings = _parse_servings(request.data.get("servings"))
            if servings in (None, "error"):
                return Response(
                    {
                        "errors": (
                            "Укажите корректное значение servings "
                            "(целое число ≥ 1)."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            obj.servings = servings
            obj.save(update_fields=["servings"])
            data = RecipeShortSerializer(
                recipe,
                context={"request": request},
            ).data
            return Response(data, status=status.HTTP_200_OK)

        deleted, _ = ShoppingCart.objects.filter(
            user=request.user,
            recipe=recipe,
        ).delete()
        if deleted == 0:
            return Response(
                {"errors": "Этого рецепта нет в списке покупок."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[AllowAny],
        url_path="get-link",
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        code = _encode_base62(int(recipe.id))
        short_url = request.build_absolute_uri(f"/s/{code}")
        return Response({"short-link": short_url}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        scale = ExpressionWrapper(
            Value(1.0)
            * Coalesce(
                F("recipe__shoppingcarts__servings"),
                F("recipe__servings"),
            )
            / F("recipe__servings"),
            output_field=FloatField(),
        )
        amount_scaled = ExpressionWrapper(
            F("amount") * scale,
            output_field=FloatField(),
        )

        items = (
            RecipeIngredient.objects.filter(
                recipe__shoppingcarts__user=request.user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(
                total=Cast(
                    Ceil(Sum(amount_scaled)),
                    IntegerField(),
                )
            )
            .order_by("ingredient__name")
        )

        lines = [
            f"{it['ingredient__name']} — {it['total']} "
            f"{it['ingredient__measurement_unit']}"
            for it in items
        ]
        content = "\n".join(lines) if lines else "Список покупок пуст."
        response = HttpResponse(
            content,
            content_type="text/plain; charset=utf-8",
        )
        response["Content-Disposition"] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


def _decode_base62(s: str) -> Optional[int]:
    try:
        n = 0
        for ch in s:
            n = n * 62 + BASE62_ALPHABET.index(ch)
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


def _encode_base62(n: int) -> str:
    if n == 0:
        return BASE62_ALPHABET[0]
    chars = []
    while n > 0:
        n, rem = divmod(n, 62)
        chars.append(BASE62_ALPHABET[rem])
    return "".join(reversed(chars))


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
        obj = (
            ShortLink.objects.select_related("recipe")
            .filter(code=code)
            .only("recipe_id")
            .first()
        )
        if obj and obj.recipe_id:
            return int(obj.recipe_id)
    except Exception:
        pass
    return None


def _resolve_recipe_id(code: str) -> Optional[int]:
    rid = _lookup_recipe_id(code)
    if rid:
        return rid

    val = _decode_base62(code)
    if isinstance(val, int):
        return val

    val = _decode_urlsafe_b64_to_int(code)
    if isinstance(val, int):
        return val

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
            return redirect(
                self.FRONT_RECIPE_PATH.format(id=rid),
                permanent=False,
            )

        return redirect("/", permanent=False)
