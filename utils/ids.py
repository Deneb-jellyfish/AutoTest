from __future__ import annotations

from typing import Iterable


def generate_prefixed_id(existing_ids: Iterable[str], prefix: str) -> str:
    numbers = []
    for value in existing_ids:
        text = str(value)
        if text.startswith(f"{prefix}-"):
            suffix = text.split("-", 1)[1]
            if suffix.isdigit():
                numbers.append(int(suffix))
    return f"{prefix}-{max(numbers, default=0) + 1:03d}"
