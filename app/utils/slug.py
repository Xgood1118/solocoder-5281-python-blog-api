from __future__ import annotations

from slugify import slugify as _slugify


def generate_slug(text: str) -> str:
    return _slugify(text, lowercase=True, separator="-")
