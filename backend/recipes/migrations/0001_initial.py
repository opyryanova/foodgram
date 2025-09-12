# Generated to match models as of 2025-09-11
from django.conf import settings
from django.db import migrations, models
from django.db.models.functions import Lower
import django.db.models.deletion
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator


def get_user_model_label():
    """
    В settings.AUTH_USER_MODEL может быть не 'auth.User'.
    Оставляем ссылку в ForeignKey на settings.AUTH_USER_MODEL через migrations.swappable_dependency.
    """
    return settings.AUTH_USER_MODEL


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(get_user_model_label()),
    ]

    operations = [
        # Tag
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField('Название', max_length=64, unique=True, db_index=True)),
                ('slug', models.SlugField(
                    'Slug', max_length=32, unique=True,
                    validators=[RegexValidator(regex=r'^[-a-zA-Z0-9_]+$', message='Разрешены латиница, цифры, дефис и нижнее подчеркивание.')],
                    db_index=True
                )),
            ],
            options={
                'verbose_name': 'Тег',
                'verbose_name_plural': 'Теги',
                'ordering': ['name'],
            },
        ),

        # Ingredient
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField('Название', max_length=128, db_index=True)),
                ('measurement_unit', models.CharField('Единица измерения', max_length=64)),
            ],
            options={
                'verbose_name': 'Ингредиент',
                'verbose_name_plural': 'Ингредиенты',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='ingredient',
            index=models.Index(Lower('name'), name='ingredient_name_lci_idx'),
        ),
        migrations.AddConstraint(
            model_name='ingredient',
            constraint=models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='ingredient_name_unit_unique'
            ),
        ),

        # Recipe
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField('Название', max_length=256, db_index=True)),
                ('image', models.ImageField('Картинка', upload_to='recipes/')),
                ('text', models.TextField('Описание')),
                ('cooking_time', models.PositiveIntegerField('Время готовки, мин',
                    validators=[MinValueValidator(1, message='Минимум 1 минута.')])),
                ('servings', models.PositiveSmallIntegerField(
                    'Количество порций', default=1,
                    validators=[MinValueValidator(1), MaxValueValidator(50)],
                    help_text='На сколько порций рассчитан рецепт.'
                )),
                ('pub_date', models.DateTimeField('Дата публикации', auto_now_add=True)),
                ('author', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='recipes',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Автор'
                )),
            ],
            options={
                'verbose_name': 'Рецепт',
                'verbose_name_plural': 'Рецепты',
                'ordering': ['-pub_date'],
            },
        ),
        migrations.AddConstraint(
            model_name='recipe',
            constraint=models.UniqueConstraint(
                fields=('author', 'name'),
                name='unique_author_recipe_name'
            ),
        ),

        # RecipeIngredient (through)
        migrations.CreateModel(
            name='RecipeIngredient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.PositiveIntegerField('Количество',
                    validators=[MinValueValidator(1, message='Количество должно быть не меньше 1.')])),

                ('ingredient', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ingredient_recipes',
                    to='recipes.Ingredient'
                )),
                ('recipe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='recipe_ingredients',
                    to='recipes.Recipe'
                )),
            ],
            options={
                'verbose_name': 'Ингредиент в рецепте',
                'verbose_name_plural': 'Ингредиенты в рецепте',
            },
        ),
        migrations.AddConstraint(
            model_name='recipeingredient',
            constraint=models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient'
            ),
        ),

        # ManyToMany Recipe.tags & Recipe.ingredients (through set)
        migrations.AddField(
            model_name='recipe',
            name='tags',
            field=models.ManyToManyField(related_name='recipes', to='recipes.Tag', verbose_name='Теги'),
        ),
        migrations.AddField(
            model_name='recipe',
            name='ingredients',
            field=models.ManyToManyField(
                through='recipes.RecipeIngredient',
                related_name='recipes',
                to='recipes.Ingredient',
                verbose_name='Ингредиенты'
            ),
        ),

        # Favorite
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='favorites',
                    to='recipes.Recipe'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='favorites',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Избранное',
                'verbose_name_plural': 'Избранное',
            },
        ),
        migrations.AddConstraint(
            model_name='favorite',
            constraint=models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite_user_recipe'
            ),
        ),

        # ShoppingCart
        migrations.CreateModel(
            name='ShoppingCart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('servings', models.PositiveSmallIntegerField(
                    'Порций для покупки', null=True, blank=True,
                    validators=[MinValueValidator(1)],
                    help_text='Сколько порций планируете купить; если пусто — как в рецепте.'
                )),
                ('recipe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='shoppingcarts',
                    to='recipes.Recipe'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cart',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Покупка',
                'verbose_name_plural': 'Список покупок',
            },
        ),
        migrations.AddConstraint(
            model_name='shoppingcart',
            constraint=models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_cart_user_recipe'
            ),
        ),

        # Subscription
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='followers',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Автор'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='follows',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Подписчик'
                )),
            ],
            options={
                'verbose_name': 'Подписка',
                'verbose_name_plural': 'Подписки',
            },
        ),
        migrations.AddConstraint(
            model_name='subscription',
            constraint=models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_follow'
            ),
        ),
        migrations.AddConstraint(
            model_name='subscription',
            constraint=models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='prevent_self_follow'
            ),
        ),

        # ShortLink
        migrations.CreateModel(
            name='ShortLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField('Код', max_length=16, unique=True, db_index=True)),
                ('recipe', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='shortlink',
                    to='recipes.Recipe'
                )),
            ],
            options={
                'verbose_name': 'Короткая ссылка',
                'verbose_name_plural': 'Короткие ссылки',
            },
        ),
    ]
