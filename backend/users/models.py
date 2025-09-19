from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator
from django.db import models
from django.db.models.functions import Lower
from django.db.models.signals import post_save
from django.dispatch import receiver

from users.validators import USERNAME_VALIDATORS


class User(AbstractUser):
    first_name = models.CharField("Имя", max_length=150, blank=False)
    last_name  = models.CharField("Фамилия", max_length=150, blank=False)
    
    username = models.CharField(
        "Имя пользователя",
        max_length=150,
        unique=True,
        help_text=(
            "Обязательное поле. До 150 символов. "
            "Только буквы, цифры и @/./+/-/_."
        ),
        validators=USERNAME_VALIDATORS,
        error_messages={
            "unique": "Пользователь с таким username уже существует.",
        },
    )

    email = models.EmailField(
        "Email",
        blank=False,
        null=False,
        validators=[EmailValidator()],
        db_index=True,
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="user_email_ci_unique",
                violation_error_message=(
                    "Пользователь с таким email уже существует."
                ),
            ),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.username or self.email


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь",
    )
    avatar = models.ImageField(
        "Аватар",
        upload_to="avatars/",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self) -> str:
        name = self.user.username or self.user.email
        return f"Профиль {name}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
