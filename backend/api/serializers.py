from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from django.db.models import Q

from djoser.serializers import (
    TokenCreateSerializer as DjoserTokenCreateSerializer,
)
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from api.constants import (
    MAX_SERVINGS,
    MIN_AMOUNT,
    MIN_COOKING_TIME,
    MIN_SERVINGS,
)

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Subscription,
    Tag,
)
from users.models import Profile, User


class UserInfoSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "avatar",
            "shopping_cart_count",
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
        if hasattr(obj, "profile") and obj.profile.avatar:
            url = obj.profile.avatar.url
            return request.build_absolute_uri(url) if request else url
        return ""


class UserCreateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=150,
    )
    last_name = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=150,
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        allow_blank=False,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
        )
        extra_kwargs = {"password": {"write_only": True}}

    def validate_first_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Обязательное поле.")
        return value

    def validate_last_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Обязательное поле.")
        return value

    def validate_email(self, value):
        val = (value or "").strip().lower()
        if not val:
            raise serializers.ValidationError("Укажите email.")
        if User.objects.filter(email__iexact=val).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует."
            )
        return val

    def create(self, validated_data):
        try:
            user = User.objects.create_user(**validated_data)
        except IntegrityError as exc:
            msg = str(exc).lower()
            if "username" in msg:
                raise serializers.ValidationError(
                    {
                        "username": [
                            "Пользователь с таким username уже существует."
                        ]
                    }
                )
            if "email" in msg:
                raise serializers.ValidationError(
                    {"email": ["Пользователь с таким email уже существует."]}
                )
            raise
        Profile.objects.get_or_create(user=user)
        return user


class SetUserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True, help_text="Изображение в base64")

    class Meta:
        model = Profile
        fields = ("avatar",)

    def update(self, instance, validated_data):
        if instance.avatar:
            instance.avatar.delete(save=False)
        instance.avatar = validated_data["avatar"]
        instance.save(update_fields=["avatar"])
        return instance


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = ("id", "name", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")
        read_only_fields = ("id", "name", "measurement_unit")
        validators = [
            UniqueTogetherValidator(
                queryset=Ingredient.objects.all(),
                fields=("name", "measurement_unit"),
                message=(
                    "Ингредиент с такой парой (name, measurement_unit) "
                    "уже существует."
                ),
            )
        ]


class RecipeIngredientReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    measurement_unit = serializers.CharField()
    amount = serializers.IntegerField()


class RecipeIngredientWriteSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=MIN_AMOUNT)


class RecipeShortSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class ServingsPayload(serializers.Serializer):
    servings = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )


class SetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        required=True,
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
    )

    def validate_current_password(self, value):
        user = self.context.get("request").user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context.get("request").user)
        return value


class RecipeSerializer(serializers.ModelSerializer):
    author = UserInfoSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
            "servings",
        )
        read_only_fields = fields

    def _through_qs(self, recipe):
        through = Recipe.ingredients.through
        return through.objects.filter(
            recipe=recipe
        ).select_related("ingredient")

    def get_ingredients(self, obj):
        data = []
        for ri in self._through_qs(obj):
            ing = ri.ingredient
            data.append(
                {
                    "id": ing.id,
                    "name": ing.name,
                    "measurement_unit": ing.measurement_unit,
                    "amount": ri.amount,
                }
            )
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
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class RecipeWriteSerializer(serializers.ModelSerializer):
    author = UserInfoSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    ingredients = RecipeIngredientWriteSerializer(many=True)
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(min_value=MIN_COOKING_TIME)
    servings = serializers.IntegerField(
        min_value=MIN_SERVINGS,
        max_value=MAX_SERVINGS,
        required=False,
    )

    class Meta:
        model = Recipe
        fields = (
            "id",
            "ingredients",
            "tags",
            "image",
            "name",
            "text",
            "cooking_time",
            "author",
            "servings",
        )
        read_only_fields = ("id", "author")

    def validate(self, data):
        creating = self.instance is None
        incoming = getattr(self, "initial_data", {}) or {}

        if creating or ("tags" in incoming):
            tags = data.get("tags")
            if creating and not tags:
                raise serializers.ValidationError("Добавьте хотя бы один тег.")
            if "tags" in incoming:
                if not tags:
                    raise serializers.ValidationError(
                        "Добавьте хотя бы один тег."
                    )
                tag_ids = [t.id for t in tags]
                if len(tag_ids) != len(set(tag_ids)):
                    raise serializers.ValidationError(
                        "Теги не должны повторяться."
                    )

        if creating or ("ingredients" in incoming):
            ingredients = data.get("ingredients")
            if creating and not ingredients:
                raise serializers.ValidationError(
                    "Добавьте хотя бы один ингредиент."
                )
            if "ingredients" in incoming:
                if not ingredients:
                    raise serializers.ValidationError(
                        "Добавьте хотя бы один ингредиент."
                    )
                ids_ = [item["id"].id for item in ingredients]
                if len(ids_) != len(set(ids_)):
                    raise serializers.ValidationError(
                        "Ингредиенты не должны повторяться."
                    )

        return data

    @staticmethod
    def _create_ingredients(recipe, ingredients_payload):
        through = Recipe.ingredients.through
        through.objects.bulk_create(
            [
                through(
                    recipe=recipe,
                    ingredient=item["id"],
                    amount=item["amount"],
                )
                for item in ingredients_payload
            ]
        )

    def _set_tags_and_ingredients(self, recipe, tags, ingredients):
        if tags is not None:
            recipe.tags.set(tags)
        if ingredients is not None:
            self._create_ingredients(recipe, ingredients)

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        validated_data.pop("author", None)
        try:
            recipe = Recipe.objects.create(**validated_data)
            self._set_tags_and_ingredients(recipe, tags, ingredients)
            return recipe
        except IntegrityError:
            raise serializers.ValidationError(
                {"detail": "Невалидные данные рецепта."}
            )

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        tags = validated_data.pop("tags", None)

        instance = super().update(instance, validated_data)

        through = Recipe.ingredients.through
        if ingredients is not None:
            through.objects.filter(recipe=instance).delete()
            self._create_ingredients(instance, ingredients)
        if tags is not None:
            instance.tags.set(tags)

        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class SubscriptionsSerializer(UserInfoSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta(UserInfoSerializer.Meta):
        fields = UserInfoSerializer.Meta.fields + ("recipes", "recipes_count")

    def get_recipes(self, obj):
        request = self.context.get("request")
        qs = obj.recipes.all()
        raw = request.query_params.get("recipes_limit") if request else None
        if raw is not None:
            try:
                limit = int(raw)
                if limit < 0:
                    raise ValueError
                qs = qs[:limit]
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    "recipes_limit должен быть неотрицательным целым числом."
                )
        return RecipeShortSerializer(qs, many=True, context=self.context).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["recipes_count"] = instance.recipes.count()
        return data


class SubscribeAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ("author",)

    def validate_author(self, value):
        user = self.context["request"].user
        if user == value:
            raise serializers.ValidationError("Нельзя подписаться на себя.")
        if Subscription.objects.filter(user=user, author=value).exists():
            raise serializers.ValidationError(
                "Вы уже подписаны на этого пользователя."
            )
        return value

    def create(self, validated_data):
        return Subscription.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )

    def to_representation(self, instance):
        return SubscriptionsSerializer(
            instance.author, context=self.context
        ).data


class _UserRecipeRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = ("user", "recipe")

    def validate(self, attrs):
        model = self.Meta.model
        exists = model.objects.filter(
            user=attrs["user"],
            recipe=attrs["recipe"],
        ).exists()
        if exists:
            raise serializers.ValidationError(
                f"Этот рецепт уже в {model._meta.verbose_name}."
            )
        return attrs

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe, context=self.context
        ).data


class FavoriteSerializer(_UserRecipeRelationSerializer):
    class Meta(_UserRecipeRelationSerializer.Meta):
        model = Favorite


class ShoppingCartSerializer(_UserRecipeRelationSerializer):
    class Meta(_UserRecipeRelationSerializer.Meta):
        model = ShoppingCart


class LoginOrEmailTokenCreateSerializer(DjoserTokenCreateSerializer):
    login = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        username_field = getattr(self, "username_field", "email")

        raw_login = (
            attrs.get("login")
            or attrs.get(username_field)
            or attrs.get("email")
            or attrs.get("username")
            or ""
        ).strip()

        password = attrs.get("password") or ""
        if not raw_login or not password:
            raise serializers.ValidationError(
                {"non_field_errors": ["Укажите логин и пароль."]}
            )

        login_norm = raw_login.lower()

        UserModel = get_user_model()
        user = UserModel.objects.filter(
            Q(email__iexact=login_norm) | Q(username__iexact=login_norm)
        ).first()

        if not user or not user.check_password(password):
            raise serializers.ValidationError(
                {"non_field_errors": ["Неверные учетные данные."]}
            )
        if not getattr(user, "is_active", True):
            raise serializers.ValidationError(
                {"non_field_errors": ["Пользователь деактивирован."]}
            )

        attrs[username_field] = getattr(user, username_field, user.email)
        return super().validate(attrs)
