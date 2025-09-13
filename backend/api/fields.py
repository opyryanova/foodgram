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

    default_error_messages = {
        "invalid_image": "Некорректное изображение.",
        "invalid_type": "Поддерживаются только типы изображений (jpeg/png/gif/webp).",
        "not_base64": "Строка не является валидным base64-изображением.",
    }

    _ALLOWED_FORMATS = {"jpeg", "jpg", "png", "gif", "webp"}

    def to_internal_value(self, data: Any):
        if hasattr(data, "read"):
            return super().to_internal_value(data)

        if isinstance(data, str):
            data = data.strip()
            if not data:
                self.fail("invalid_image")

            if data.startswith("data:image"):
                try:
                    _, b64data = data.split(",", 1)
                except ValueError:
                    self.fail("not_base64")
                raw_b64 = b64data.strip()
            else:
                raw_b64 = data

            try:
                decoded_bytes = base64.b64decode(raw_b64, validate=True)
            except (binascii.Error, ValueError):
                self.fail("not_base64")

            try:
                with Image.open(BytesIO(decoded_bytes)) as img:
                    fmt = (img.format or "").lower()
            except (UnidentifiedImageError, OSError):
                self.fail("invalid_image")

            if fmt == "jpeg":
                fmt = "jpg"

            if fmt not in self._ALLOWED_FORMATS:
                self.fail("invalid_type")

            file_name = f"{uuid.uuid4().hex}.{fmt}"
            content = ContentFile(decoded_bytes, name=file_name)
            return super().to_internal_value(content)

        self.fail("invalid_image")
