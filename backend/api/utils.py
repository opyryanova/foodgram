from __future__ import annotations

import base64
from typing import Optional

from api.constants import BASE62_ALPHABET


INDEX62 = {ch: i for i, ch in enumerate(BASE62_ALPHABET)}

__all__ = [
    "INDEX62",
    "encode_base62",
    "decode_base62",
    "decode_urlsafe_b64_to_int",
    "_encode_base62",
    "_decode_base62",
    "_decode_urlsafe_b64_to_int",
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
        if txt.isdigit():
            return int(txt)
        digits = "".join(ch for ch in txt if ch.isdigit())
        return int(digits) if digits else None
    except Exception:
        return None


def _encode_base62(n: int) -> str:
    return encode_base62(n)


def _decode_base62(s: str) -> Optional[int]:
    return decode_base62(s)


def _decode_urlsafe_b64_to_int(s: str) -> Optional[int]:
    return decode_urlsafe_b64_to_int(s)
