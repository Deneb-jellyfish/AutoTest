from __future__ import annotations

from typing import Any, Dict, List

from core.llm_client import LlmClient
from utils.prompt_templates import REQUIREMENT_STRUCTURING_PROMPT


def split_requirements(raw_text: str) -> List[str]:
    lines = [l.strip() for l in raw_text.splitlines()]
    blocks: List[str] = []
    buf: List[str] = []
    for line in lines:
        if not line:
            if buf:
                blocks.append(" ".join(buf).strip())
                buf = []
            continue
        buf.append(line)
    if buf:
        blocks.append(" ".join(buf).strip())
    return [b for b in blocks if len(b) >= 10]


def parse_requirement(text: str, llm: LlmClient) -> Dict[str, Any]:
    return llm.json_completion(REQUIREMENT_STRUCTURING_PROMPT, text)
