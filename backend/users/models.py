from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator
from django.db import models
from django.db.models.functions import Lower
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    """
    Кастомный пользователь на базе AbstractUser.
    Улучшения:
    - email обязателен и уникален (в т.ч. с учётом регистра);
    - нормализуем email в нижний регистр перед сохранением.
    """
    email = models.EmailField(
        "Email",
        unique=True,
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
            # уникальность email без учёта регистра
            models.UniqueConstraint(
                Lower("email"),
                name="user_email_ci_unique",
                violation_error_message="Пользователь с таким email уже существует.",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.username or self.email


class Profile(models.Model):
    """
    Профиль пользователя: аватар и OneToOne-связь с User.
    Совместимо с сериализаторами и вьюхами:
    - поле avatar читается в UserSerializer как абсолютный URL.
    """
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

    def __str__(self):
        return f"Профиль {self.user.username or self.user.email}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Автосоздание Profile при регистрации.
    Совместимо с нашим UserCreateSerializer (дополнительно не мешает).
    """
    if created:
        Profile.objects.get_or_create(user=instance)
