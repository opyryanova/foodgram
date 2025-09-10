# backend/api/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet,        # наследник DjoserUserViewSet (подписки и др.)
    TagViewSet,
    IngredientViewSet,
    RecipeViewSet,
)

app_name = 'api'

router = DefaultRouter()
# Порядок не критичен, но так нагляднее
router.register('users', UserViewSet, basename='users')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    # Djoser: токен-авторизация /api/auth/token/login, /api/auth/token/logout
    path('auth/', include('djoser.urls.authtoken')),
    # Основные эндпоинты по схеме
    path('', include(router.urls)),
]
