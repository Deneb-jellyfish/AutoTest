from __future__ import annotations

import html
from typing import Any, Dict, List


def _wrap(text: str, color: str) -> str:
    safe = html.escape(text)
    return f'<span style="background:{color};padding:2px 4px;border-radius:3px">{safe}</span>'


def render_highlighted(raw_text: str, parsed: Dict[str, Any]) -> str:
    """
    Light-weight highlighting: replace substrings that appear in parsed lists.
    Colors:
      - Input fields: light blue
      - Data ranges: light yellow
      - Conditions: light red
      - Expected actions: light green
    """
    text = html.escape(raw_text)
    replacements: List[tuple[str, str]] = []
    for s in parsed.get("conditions", []) or []:
        replacements.append((s, "#FECACA"))
    for s in parsed.get("expected_actions", []) or []:
        replacements.append((s, "#BBF7D0"))
    for s in parsed.get("input_fields", []) or []:
        replacements.append((s, "#BFDBFE"))
    for s in parsed.get("data_ranges", []) or []:
        replacements.append((s, "#FEF08A"))

    # avoid nested replacements by longest-first
    replacements.sort(key=lambda x: len(x[0]), reverse=True)
    for needle, color in replacements:
        if not needle or needle not in raw_text:
            continue
        text = text.replace(html.escape(needle), _wrap(needle, color))
    return text

