from __future__ import annotations

import base64
from typing import Optional

from api.constants import BASE62_ALPHABET, FRONT_RECIPE_PATH


INDEX62 = {ch: i for i, ch in enumerate(BASE62_ALPHABET)}

__all__ = [
    "INDEX62",
    "encode_base62",
    "decode_base62",
    "decode_urlsafe_b64_to_int",
    "lookup_direct_url",
]


def encode_base62(n: int) -> str:
    if n < 0:
        raise ValueError("encode_base62: n must be non-negative")
    if n == 0:
        return BASE62_ALPHABET[0]
    chars = []
    while n > 0:
        n, rem = divmod(n, 62)
        chars.append(BASE62_ALPHABET[rem])
    return "".join(reversed(chars))


def decode_base62(s: str) -> Optional[int]:
    if not isinstance(s, str) or not s:
        return None
    try:
        n = 0
        for ch in s:
            n = n * 62 + INDEX62[ch]
        return n
    except KeyError:
        return None


def decode_urlsafe_b64_to_int(s: str) -> Optional[int]:
    if not isinstance(s, str) or not s:
        return None
    try:
        pad = "=" * (-len(s) % 4)
        raw = base64.urlsafe_b64decode(s + pad)
        txt = raw.decode("utf-8", errors="ignore")
        digits = []
        for ch in txt:
            if ch.isdigit():
                digits.append(ch)
            elif digits:
                break
        return int("".join(digits)) if digits else None
    except Exception:
        return None


def _import_shortlink_model():
    try:
        from recipes.models import ShortLink  # type: ignore
        return ShortLink
    except (ImportError, ModuleNotFoundError):
        return None


def _lookup_shortlink_target(code: str) -> Optional[str]:
    ShortLink = _import_shortlink_model()
    if not ShortLink:
        return None
    obj = ShortLink.objects.filter(code=code).only("target_url").first()
    if obj and getattr(obj, "target_url", None):
        return str(obj.target_url)
    return None


def _lookup_shortlink_recipe_id(code: str) -> Optional[int]:
    ShortLink = _import_shortlink_model()
    if not ShortLink:
        return None
    obj = (
        ShortLink.objects
        .filter(code=code)
        .only("recipe_id")
        .first()
    )
    if obj and obj.recipe_id:
        return int(obj.recipe_id)
    return None


def _resolve_recipe_id(code: str) -> Optional[int]:
    rid = _lookup_shortlink_recipe_id(code)
    if isinstance(rid, int) and rid > 0:
        return rid
    val = decode_base62(code)
    if isinstance(val, int) and val > 0:
        return val
    val = decode_urlsafe_b64_to_int(code)
    if isinstance(val, int) and val > 0:
        return val
    return None


def lookup_direct_url(code: str) -> Optional[str]:
    if not isinstance(code, str) or not code:
        return None
    code = code.strip()
    if not code:
        return None

    direct = _lookup_shortlink_target(code)
    if direct:
        return direct

    recipe_id = _resolve_recipe_id(code)
    if isinstance(recipe_id, int) and recipe_id > 0:
        return FRONT_RECIPE_PATH.format(id=recipe_id)

    return None
