"""Константы для пагинации и базовых ограничений API."""

# Пагинация
DEFAULT_PAGE_SIZE = 6
MAX_PAGE_SIZE = 20
PAGE_SIZE_QUERY_PARAM = "limit"

# Ограничения для моделей
MIN_AMOUNT = 1               # минимальное количество ингредиента
MIN_COOKING_TIME = 1         # минимальное время готовки (мин)
MAX_SERVINGS = 50            # максимальное количество порций
