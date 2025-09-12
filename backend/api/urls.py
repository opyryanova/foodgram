# backend/api/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet,        # наследник DjoserUserViewSet (me, subscriptions и др.)
    TagViewSet,
    IngredientViewSet,
    RecipeViewSet,
)

app_name = "api"

router = DefaultRouter()
# Порядок регистраций не критичен, выбрана наглядная группировка
router.register("users", UserViewSet, basename="users")
router.register("tags", TagViewSet, basename="tags")
router.register("ingredients", IngredientViewSet, basename="ingredients")
router.register("recipes", RecipeViewSet, basename="recipes")

urlpatterns = [
    # ВАЖНО: эндпоинты авторизации Djoser уже подключены в foodgram/urls.py
    # здесь повторять path('auth/', include('djoser.urls.authtoken')) не нужно,
    # чтобы не было дублей маршрутов.
    path("", include(router.urls)),
]
