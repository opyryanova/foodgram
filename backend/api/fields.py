# backend/api/fields.py
from __future__ import annotations

import base64
import binascii
import uuid
from io import BytesIO
from typing import Any

from django.core.files.base import ContentFile
from rest_framework import serializers
from PIL import Image, UnidentifiedImageError


class SmartImageField(serializers.ImageField):
    """
    Поле, которое понимает:
      - обычные файлы (multipart/form-data),
      - строки в формате base64 (в т.ч. data URI: data:image/png;base64,...)

    Использование: как обычный ImageField в сериализаторах.
    """

    default_error_messages = {
        "invalid_image": "Некорректное изображение.",
        "invalid_type": "Поддерживаются только типы изображений (jpeg/png/gif/webp).",
        "not_base64": "Строка не является валидным base64-изображением.",
    }

    # Разрешённые форматы (по данным PIL.Image.format)
    _ALLOWED_FORMATS = {"jpeg", "jpg", "png", "gif", "webp"}

    def to_internal_value(self, data: Any):
        # 1) Если пришёл уже файл -> отдадим родителю
        if hasattr(data, "read"):
            return super().to_internal_value(data)

        # 2) Если пришла строка — пытаемся распарсить base64 (data URI или «голый» base64)
        if isinstance(data, str):
            data = data.strip()
            if not data:
                self.fail("invalid_image")

            # Выделяем чистую base64-часть
            if data.startswith("data:image"):
                try:
                    _, b64data = data.split(",", 1)
                except ValueError:
                    self.fail("not_base64")
                raw_b64 = b64data.strip()
            else:
                raw_b64 = data

            # Декодирование base64 с валидацией
            try:
                decoded_bytes = base64.b64decode(raw_b64, validate=True)
            except (binascii.Error, ValueError):
                self.fail("not_base64")

            # Проверяем, что это действительно изображение, и узнаём формат через Pillow
            try:
                with Image.open(BytesIO(decoded_bytes)) as img:
                    fmt = (img.format or "").lower()
            except (UnidentifiedImageError, OSError):
                self.fail("invalid_image")

            # Нормализуем jpeg -> jpg
            if fmt == "jpeg":
                fmt = "jpg"

            if fmt not in self._ALLOWED_FORMATS:
                self.fail("invalid_type")

            # Создаём временный файл для DRF
            file_name = f"{uuid.uuid4().hex}.{fmt}"
            content = ContentFile(decoded_bytes, name=file_name)
            return super().to_internal_value(content)

        # 3) Иное — не поддерживаем
        self.fail("invalid_image")
