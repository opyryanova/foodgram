# backend/recipes/models.py
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower   # ✦ для функционального индекса

User = settings.AUTH_USER_MODEL

slug_validator = RegexValidator(
    regex=r"^[-a-zA-Z0-9_]+$",
    message="Разрешены латиница, цифры, дефис и нижнее подчеркивание."
)


class Tag(models.Model):
    name = models.CharField("Название", max_length=64, unique=True, db_index=True)  # ✦ db_index
    slug = models.SlugField("Slug", max_length=32, unique=True, validators=[slug_validator], db_index=True)  # ✦ db_index

    class Meta:
        ordering = ["name"]
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField("Название", max_length=128, db_index=True)  # ✦ db_index полезен для поиска
    measurement_unit = models.CharField("Единица измерения", max_length=64)

    class Meta:
        ordering = ["name"]
        unique_together = [("name", "measurement_unit")]
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        indexes = [
            models.Index(Lower("name"), name="ingredient_name_lci_idx"),  # ✦ уже было — оставляем
        ]

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recipes", verbose_name="Автор")
    name = models.CharField("Название", max_length=256, db_index=True)  # ✦ db_index для поиска
    image = models.ImageField("Картинка", upload_to="recipes/")
    text = models.TextField("Описание")
    cooking_time = models.PositiveIntegerField(
        "Время готовки, мин",
        validators=[MinValueValidator(1, message="Минимум 1 минута.")]
    )
    tags = models.ManyToManyField(Tag, related_name="recipes", verbose_name="Теги")
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", related_name="recipes", verbose_name="Ингредиенты"
    )
    servings = models.PositiveSmallIntegerField(
        "Количество порций",
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="На сколько порций рассчитан рецепт."
    )
    pub_date = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta:
        ordering = ["-pub_date"]
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        constraints = [
            models.UniqueConstraint(fields=["author", "name"], name="unique_author_recipe_name")
        ]

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="ingredient_recipes")
    amount = models.PositiveIntegerField(
        "Количество",
        validators=[MinValueValidator(1, message="Количество должно быть не меньше 1.")]
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецепте"
        constraints = [
            models.UniqueConstraint(fields=["recipe", "ingredient"], name="unique_recipe_ingredient")
        ]

    def __str__(self):
        return f"{self.ingredient} x {self.amount}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = [
            models.UniqueConstraint(fields=["user", "recipe"], name="unique_favorite_user_recipe")
        ]

    def __str__(self):
        return f"{self.user} → {self.recipe}"


class ShoppingCart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="in_carts")

    class Meta:
        verbose_name = "Покупка"
        verbose_name_plural = "Список покупок"
        constraints = [
            models.UniqueConstraint(fields=["user", "recipe"], name="unique_cart_user_recipe")
        ]

    def __str__(self):
        return f"{self.user} → {self.recipe}"


class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follows", verbose_name="Подписчик")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers", verbose_name="Автор")

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(fields=["user", "author"], name="unique_follow"),
            models.CheckConstraint(check=~models.Q(user=models.F("author")), name="prevent_self_follow"),
        ]

    def __str__(self):
        return f"{self.user} → {self.author}"


class ShortLink(models.Model):
    recipe = models.OneToOneField(Recipe, on_delete=models.CASCADE, related_name="shortlink")
    code = models.CharField("Код", max_length=16, unique=True, db_index=True)  # ✦ db_index

    class Meta:
        verbose_name = "Короткая ссылка"
        verbose_name_plural = "Короткие ссылки"

    def __str__(self):
        return self.code
