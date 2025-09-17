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
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    FavoriteSerializer,
    IngredientSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    RecipeWriteSerializer,
    ServingsPayload,
    SetPasswordSerializer,
    SetUserAvatarSerializer,
    ShoppingCartSerializer,
    SubscribeAuthorSerializer,
    SubscriptionsSerializer,
    TagSerializer,
    UserCreateSerializer,
    UserInfoSerializer,
)
from api.utils import (
    encode_base62,
    decode_base62,
    decode_urlsafe_b64_to_int,
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


class UserViewSet(viewsets.ModelViewSet):
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
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("list", "retrieve"):
            return UserInfoSerializer
        if self.action == "subscriptions":
            return SubscriptionsSerializer
        if self.action == "subscribe":
            return SubscribeAuthorSerializer
        if self.action == "set_avatar":
            return SetUserAvatarSerializer
        return UserInfoSerializer

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="me",
    )
    def me(self, request):
        serializer = UserInfoSerializer(request.user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request):
        authors = User.objects.filter(
            followers__user=request.user
        ).order_by("id")
        page = self.paginate_queryset(authors)
        serializer = self.get_serializer(
            page or authors, many=True, context={"request": request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="set_password",
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="subscribe",
    )
    def subscribe(self, request, *args, **kwargs):
        author = self.get_object()
        method = request.method.lower()

        if method == "post":
            serializer = SubscribeAuthorSerializer(
                data={"author": author.id},
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            data = SubscriptionsSerializer(
                author, context={"request": request}
            ).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = Subscription.objects.filter(
            user=request.user, author=author
        ).delete()
        if not deleted:
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
                user=user, recipe=OuterRef("pk")
            )
            cart_exists = ShoppingCart.objects.filter(
                user=user, recipe=OuterRef("pk")
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
            serializer = FavoriteSerializer(
                data={"user": request.user.id, "recipe": recipe.id},
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            data = RecipeShortSerializer(
                recipe, context={"request": request}
            ).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
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
        method = request.method.lower()

        if method == "post":
            payload = ServingsPayload(data=request.data)
            payload.is_valid(raise_exception=True)
            servings = payload.validated_data.get("servings")

            serializer = ShoppingCartSerializer(
                data={"user": request.user.id, "recipe": recipe.id},
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            if servings is not None:
                instance.servings = servings
                instance.save(update_fields=["servings"])

            data = RecipeShortSerializer(
                recipe, context={"request": request}
            ).data
            return Response(data, status=status.HTTP_201_CREATED)

        if method == "patch":
            obj = ShoppingCart.objects.filter(
                user=request.user, recipe=recipe
            ).first()
            if not obj:
                return Response(
                    {"errors": "Этого рецепта нет в списке покупок."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            payload = ServingsPayload(data=request.data)
            payload.is_valid(raise_exception=True)
            servings = payload.validated_data.get("servings")
            if servings is None:
                return Response(
                    {
                        "errors": (
                            "Укажите корректное значение servings "
                            "(целое число \u2265 1)."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            obj.servings = servings
            obj.save(update_fields=["servings"])
            data = RecipeShortSerializer(
                recipe, context={"request": request}
            ).data
            return Response(data, status=status.HTTP_200_OK)

        deleted, _ = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
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
        code = encode_base62(int(recipe.id))
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
            F("amount") * scale, output_field=FloatField()
        )
        items = (
            RecipeIngredient.objects.filter(
                recipe__shoppingcarts__user=request.user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(
                total=Cast(Ceil(Sum(amount_scaled)), IntegerField())
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
            content, content_type="text/plain; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


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
    val = decode_base62(code)
    if isinstance(val, int):
        return val
    val = decode_urlsafe_b64_to_int(code)
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
                self.FRONT_RECIPE_PATH.format(id=rid), permanent=False
            )
        return redirect("/", permanent=False)
