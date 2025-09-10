# backend/api/serializers.py
"""Сериализаторы API: пользователи, теги, ингредиенты, рецепты и связи."""

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (
    Ingredient,
    Recipe,
    Tag,
    Favorite,
    ShoppingCart,
    Subscription,
)
from users.models import User, Profile

# Минимальные значения
MIN_AMOUNT = 1
MIN_COOKING_TIME = 1


# ---------- Пользователи ----------

class UserSerializer(serializers.ModelSerializer):
    """Публичное представление пользователя."""
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "username", "first_name", "last_name",
            "email", "is_subscribed", "avatar",
        )
        read_only_fields = fields

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or user.is_anonymous:
            return False
        return Subscription.objects.filter(user=user, author=obj).exists()

    def get_avatar(self, obj):
        request = self.context.get("request")
        # Аватар хранится в Profile
        if hasattr(obj, "profile") and obj.profile.avatar:
            return (
                request.build_absolute_uri(obj.profile.avatar.url)
                if request else obj.profile.avatar.url
            )
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """Регистрация пользователя."""

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Profile.objects.get_or_create(user=user)
        return user


class AvatarSerializer(serializers.ModelSerializer):
    """Загрузка/замена аватара пользователя (модель Profile)."""
    avatar = Base64ImageField(required=True, help_text="Изображение в base64")

    class Meta:
        model = Profile
        fields = ("avatar",)

    def update(self, instance, validated_data):
        # При замене старый файл удаляем
        if instance.avatar:
            instance.avatar.delete(save=False)
        instance.avatar = validated_data["avatar"]
        instance.save(update_fields=["avatar"])
        return instance


# ---------- Справочники (теги/ингредиенты) ----------

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"
        read_only_fields = fields


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=Ingredient.objects.all(),
                fields=("name", "measurement_unit"),
                message="Ингредиент с такой парой (name, measurement_unit) уже существует.",
            )
        ]


# ---------- Ингредиенты рецепта ----------

class RecipeIngredientReadSerializer(serializers.Serializer):
    """Отображение ингредиента внутри рецепта (read-only)."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    measurement_unit = serializers.CharField()
    amount = serializers.IntegerField()


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """Передача ингредиента при создании/редактировании рецепта."""
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(
        validators=[MinValueValidator(MIN_AMOUNT, f"Количество должно быть ≥ {MIN_AMOUNT}.")]
    )


# ---------- Рецепты ----------

class ShortRecipeSerializer(serializers.ModelSerializer):
    """Короткая карточка рецепта (для избранного/подписок/корзины)."""
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class RecipeReadSerializer(serializers.ModelSerializer):
    """Просмотр рецепта (read)."""
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id", "tags", "author", "ingredients",
            "is_favorited", "is_in_shopping_cart",
            "name", "image", "text", "cooking_time",
            "servings",  # счетчик порций — для корректных калькуляций на фронте
        )
        read_only_fields = fields

    def _through_qs(self, recipe):
        Through = Recipe.ingredients.through
        return (Through.objects
                .filter(recipe=recipe)
                .select_related("ingredient"))

    def get_ingredients(self, obj):
        # Возвращаем ровно тот формат, что ожидает фронт/спека (amount — итоговое количество для рецепта)
        data = []
        for ri in self._through_qs(obj):
            ing = ri.ingredient
            data.append({
                "id": ing.id,
                "name": ing.name,
                "measurement_unit": ing.measurement_unit,
                "amount": ri.amount,
            })
        return data

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Создание/редактирование рецепта (write)."""
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    ingredients = RecipeIngredientWriteSerializer(many=True)
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(
        validators=[MinValueValidator(MIN_COOKING_TIME, f"Время должно быть ≥ {MIN_COOKING_TIME} минут.")]
    )
    # Счетчик порций — опционально, но если прислали, проверим разумные рамки
    servings = serializers.IntegerField(min_value=1, max_value=50, required=False)

    class Meta:
        model = Recipe
        fields = (
            "id", "ingredients", "tags", "image",
            "name", "text", "cooking_time", "author",
            "servings",
        )
        read_only_fields = ("id", "author")

    def validate_cooking_time(self, value):
        if not isinstance(value, int) or value < MIN_COOKING_TIME:
            raise ValidationError(f"Время должно быть целым числом ≥ {MIN_COOKING_TIME}.")
        return value

    def validate(self, data):
        tags = data.get("tags") or []
        if not tags:
            raise ValidationError("Добавьте хотя бы один тег.")
        if len(tags) != len(set(tags)):
            raise ValidationError("Теги не должны повторяться.")

        ingredients = data.get("ingredients") or []
        if not ingredients:
            raise ValidationError("Добавьте хотя бы один ингредиент.")
        ids = [item["id"].id for item in ingredients]
        if len(ids) != len(set(ids)):
            raise ValidationError("Ингредиенты не должны повторяться.")
        return data

    @staticmethod
    def _create_ingredients(recipe, ingredients_payload):
        Through = Recipe.ingredients.through
        Through.objects.bulk_create([
            Through(recipe=recipe, ingredient=item["id"], amount=item["amount"])
            for item in ingredients_payload
        ])

    def _set_tags_and_ingredients(self, recipe, tags, ingredients):
        recipe.tags.set(tags)
        self._create_ingredients(recipe, ingredients)

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        recipe = Recipe.objects.create(author=self.context["request"].user, **validated_data)
        self._set_tags_and_ingredients(recipe, tags, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        tags = validated_data.pop("tags", None)

        instance = super().update(instance, validated_data)

        Through = Recipe.ingredients.through
        if ingredients is not None:
            Through.objects.filter(recipe=instance).delete()
            self._create_ingredients(instance, ingredients)
        if tags is not None:
            instance.tags.set(tags)

        return instance

    def to_representation(self, instance):
        # Единый формат ответа
        return RecipeReadSerializer(instance, context=self.context).data


# ---------- Подписки ----------

class SubscriptionSerializer(UserSerializer):
    """Отображение автора в списке подписок с его рецептами."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("recipes", "recipes_count")

    def get_recipes(self, obj):
        request = self.context.get("request")
        qs = obj.recipes.all()
        # recipes_limit — необязательный параметр
        raw = request.query_params.get("recipes_limit") if request else None
        if raw is not None:
            try:
                limit = int(raw)
                if limit < 0:
                    raise ValueError
                qs = qs[:limit]
            except (ValueError, TypeError):
                raise ValidationError("recipes_limit должен быть неотрицательным целым числом.")
        return ShortRecipeSerializer(qs, many=True, context=self.context).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["recipes_count"] = instance.recipes.count()
        return data


class SubscribeSerializer(serializers.ModelSerializer):
    """Создание/удаление подписки."""
    class Meta:
        model = Subscription
        fields = ("author",)

    def validate_author(self, value):
        user = self.context["request"].user
        if user == value:
            raise ValidationError("Нельзя подписаться на себя.")
        if Subscription.objects.filter(user=user, author=value).exists():
            raise ValidationError("Вы уже подписаны на этого пользователя.")
        return value

    def create(self, validated_data):
        return Subscription.objects.create(
            user=self.context["request"].user, **validated_data
        )

    def to_representation(self, instance):
        return SubscriptionSerializer(instance.author, context=self.context).data


# ---------- Избранное и Корзина ----------

class _UserRecipeRelationSerializer(serializers.ModelSerializer):
    """База для Favorite/ShoppingCart с защитой от дублей."""
    class Meta:
        model = None
        fields = ("user", "recipe")

    def validate(self, attrs):
        model = self.Meta.model
        if model.objects.filter(user=attrs["user"], recipe=attrs["recipe"]).exists():
            raise ValidationError(f"Этот рецепт уже в {model._meta.verbose_name}.")
        return attrs

    def to_representation(self, instance):
        return ShortRecipeSerializer(instance.recipe, context=self.context).data


class FavoriteSerializer(_UserRecipeRelationSerializer):
    class Meta(_UserRecipeRelationSerializer.Meta):
        model = Favorite


class ShoppingCartSerializer(_UserRecipeRelationSerializer):
    class Meta(_UserRecipeRelationSerializer.Meta):
        model = ShoppingCart


# ---------- Алиасы имен под используемые во вьюхах ----------

UserInfoSerializer = UserSerializer
SetUserAvatarSerializer = AvatarSerializer
SubscriptionsSerializer = SubscriptionSerializer
SubscribeAuthorSerializer = SubscribeSerializer
RecipeShortSerializer = ShortRecipeSerializer
RecipeSerializer = RecipeReadSerializer
