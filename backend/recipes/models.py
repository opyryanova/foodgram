from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from recipes.constants import (
    TAG_NAME_MAX_LEN,
    TAG_SLUG_MAX_LEN,
    INGREDIENT_NAME_MAX_LEN,
    INGREDIENT_UNIT_MAX_LEN,
    RECIPE_NAME_MAX_LEN,
    COOKING_TIME_MIN,
    SHORTLINK_CODE_MAX_LEN,
)
from recipes.validators import SLUG_VALIDATOR

User = settings.AUTH_USER_MODEL


class Tag(models.Model):
    name = models.CharField(
        "Название",
        max_length=TAG_NAME_MAX_LEN,
        unique=True,
        db_index=True,
    )
    slug = models.SlugField(
        "Слаг",
        max_length=TAG_SLUG_MAX_LEN,
        unique=True,
        validators=[SLUG_VALIDATOR],
        db_index=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self) -> str:
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        "Название",
        max_length=INGREDIENT_NAME_MAX_LEN,
        db_index=True,
    )
    measurement_unit = models.CharField(
        "Единица измерения",
        max_length=INGREDIENT_UNIT_MAX_LEN,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        indexes = [
            models.Index(
                Lower("name"),
                name="ingredient_name_lci_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"],
                name="ingredient_name_unit_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор",
    )
    name = models.CharField(
        "Название",
        max_length=RECIPE_NAME_MAX_LEN,
        db_index=True,
    )
    image = models.ImageField("Картинка", upload_to="recipes/")
    text = models.TextField("Описание")
    cooking_time = models.PositiveIntegerField(
        "Время готовки, мин",
        validators=[
            MinValueValidator(COOKING_TIME_MIN, message="Минимум 1 минута.")
        ],
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="recipes",
        verbose_name="Теги",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes",
        verbose_name="Ингредиенты",
    )
    pub_date = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta:
        ordering = ["-pub_date"]
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        constraints = [
            models.UniqueConstraint(
                fields=["author", "name"],
                name="unique_author_recipe_name",
            )
        ]

    def __str__(self) -> str:
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="ingredient_recipes",
    )
    amount = models.PositiveIntegerField(
        "Количество",
        validators=[
            MinValueValidator(
                1,
                message="Количество должно быть не меньше 1."
            ),
        ],
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецепте"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient",
            )
        ]

    def __str__(self) -> str:
        return f"{self.ingredient} x {self.amount}"


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorites",
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_favorite_user_recipe",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.recipe}"


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_user',
        verbose_name='Добавил в корзину'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_recipe',
        verbose_name='Рецепт в корзине'
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзина'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_ShoppingCart'
            )
        ]

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follows",
        verbose_name="Подписчик",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="followers",
        verbose_name="Автор",
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"],
                name="unique_follow",
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F("author")),
                name="prevent_self_follow",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.author}"


class ShortLink(models.Model):
    recipe = models.OneToOneField(
        Recipe,
        on_delete=models.CASCADE,
        related_name="shortlink",
    )
    code = models.CharField(
        "Код",
        max_length=SHORTLINK_CODE_MAX_LEN,
        unique=True,
        db_index=True,
    )

    class Meta:
        verbose_name = "Короткая ссылка"
        verbose_name_plural = "Короткие ссылки"

    def __str__(self) -> str:
        return self.code
