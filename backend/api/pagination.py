"""Кастомный пагинатор для API."""

from rest_framework.pagination import PageNumberPagination

from .constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PAGE_SIZE_QUERY_PARAM


class PageNumberPagination(PageNumberPagination):
    """Пагинатор с поддержкой параметра limit."""

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = PAGE_SIZE_QUERY_PARAM
    max_page_size = MAX_PAGE_SIZE
