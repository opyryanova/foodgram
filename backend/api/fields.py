# backend/api/fields.py
import base64
import binascii
import imghdr
import uuid
from typing import Any

from django.core.files.base import ContentFile
from rest_framework import serializers


class SmartImageField(serializers.ImageField):
    """
    Поле, которое понимает:
      - обычные файлы (multipart/form-data),
      - строки в формате base64 (в т.ч. data URI: data:image/png;base64,....)

    Использование: так же, как обычный ImageField в сериализаторах.
    """

    default_error_messages = {
        "invalid_image": "Некорректное изображение.",
        "invalid_type": "Поддерживаются только типы изображений (jpeg/png/gif/webp).",
        "not_base64": "Строка не является валидным base64-изображением.",
    }

    # допустимые расширения для безопасности
    _ALLOWED_EXTS = {"jpeg", "jpg", "png", "gif", "webp"}

    def to_internal_value(self, data: Any):
        # 1) Если пришёл уже файл -> отдадим родителю
        if hasattr(data, "read"):
            return super().to_internal_value(data)

        # 2) Если пришла строка — пытаемся распарсить base64
        if isinstance(data, str):
            data = data.strip()

            # data URI формат: data:image/png;base64,AAAA...
            if data.startswith("data:image"):
                try:
                    header, b64data = data.split(",", 1)
                except ValueError:
                    self.fail("not_base64")

                try:
                    decoded_file = base64.b64decode(b64data)
                except (TypeError, binascii.Error):
                    self.fail("not_base64")

            else:
                # «голый» base64 без заголовка
                try:
                    decoded_file = base64.b64decode(data)
                except (TypeError, binascii.Error):
                    self.fail("not_base64")

            # определяем расширение
            file_ext = imghdr.what(None, decoded_file) or "jpg"
            if file_ext == "jpeg":
                # имghdr возвращает 'jpeg' для jpg
                file_ext = "jpg"

            if file_ext.lower() not in self._ALLOWED_EXTS:
                self.fail("invalid_type")

            file_name = f"{uuid.uuid4().hex}.{file_ext}"
            content = ContentFile(decoded_file, name=file_name)
            return super().to_internal_value(content)

        # 3) Иное — не поддерживаем
        self.fail("invalid_image")
