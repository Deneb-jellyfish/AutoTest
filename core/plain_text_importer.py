from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from core.llm_client import LlmClient


TOP_LEVEL_SPLIT_PROMPT = """
你是一名需求分析助手。
请从输入文本中提取“顶层需求”。

重要规则：
- 只保留顶层需求，不要拆成 actor/action/condition 这种细粒度字段
- 如果一条长句描述的是同一个需求，不要切碎
- 如果多个编号条目明显是不同需求，则分别提取
- 只返回 JSON 数组，不要附加解释

格式：
[
  {
    "title": "简短标题",
    "raw_text": "原始需求文本",
    "source_annotations": [
      {"text": "原文片段", "category": "top_level_requirement"}
    ]
  }
]
""".strip()


REQUIREMENT_TRIGGER_WORDS = [
    "shall",
    "must",
    "should",
    "may",
    "应",
    "应该",
    "必须",
    "可以",
    "不得",
    "不能",
    "需要",
]


def _normalize_plain_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u3000", " ").replace("\t", " ")
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"[ ]{2,}", " ", normalized)
    return normalized.strip()


def _contains_requirement_signal(text: str) -> bool:
    lower_text = text.lower()
    return any(token in lower_text for token in REQUIREMENT_TRIGGER_WORDS)


def _guess_title(text: str, index: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return f"Requirement {index}"
    return cleaned[:36] if len(cleaned) <= 36 else f"{cleaned[:33]}..."


def _split_numbered_blocks(text: str) -> List[str]:
    pattern = re.compile(r"(?m)^\s*(?:\d+[\.\)]|[A-Za-z][\.\)]|[一二三四五六七八九十]+、|[-*•])\s+")
    matches = list(pattern.finditer(text))
    if not matches:
        return []

    blocks = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        block = pattern.sub("", block, count=1).strip()
        if block:
            blocks.append(block)
    return blocks


def _split_paragraphs(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[。！？!?;；.])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _rule_extract_requirements(text: str) -> List[Dict[str, Any]]:
    blocks = _split_numbered_blocks(text)
    if not blocks:
        paragraphs = _split_paragraphs(text)
        blocks = [part for part in paragraphs if _contains_requirement_signal(part)]
    if not blocks:
        sentences = _split_sentences(text)
        blocks = [part for part in sentences if _contains_requirement_signal(part)]
    if not blocks and text.strip():
        blocks = [text.strip()]

    requirements = []
    for index, block in enumerate(blocks, start=1):
        requirements.append(
            {
                "title": _guess_title(block, index),
                "raw_text": block,
                "source_annotations": [{"text": block[:80], "category": "top_level_requirement"}],
            }
        )
    return requirements


def _llm_extract_requirements(text: str, llm_client: LlmClient) -> List[Dict[str, Any]]:
    result = llm_client.json_any_completion(TOP_LEVEL_SPLIT_PROMPT, text)
    if not isinstance(result, list):
        raise ValueError("LLM splitter must return a JSON list.")
    output = []
    for index, item in enumerate(result, start=1):
        if not isinstance(item, dict):
            continue
        raw_text = str(item.get("raw_text", "")).strip()
        if not raw_text:
            continue
        output.append(
            {
                "title": str(item.get("title", "")).strip() or _guess_title(raw_text, index),
                "raw_text": raw_text,
                "source_annotations": item.get("source_annotations") or [{"text": raw_text[:80], "category": "top_level_requirement"}],
            }
        )
    if not output:
        raise ValueError("LLM splitter returned no usable requirements.")
    return output


def extract_requirements_from_plain_text(
    raw_text: str,
    use_llm: bool = False,
    llm_client: Optional[LlmClient] = None,
) -> Dict[str, Any]:
    normalized = _normalize_plain_text(raw_text)
    if not normalized:
        return {"requirements": [], "method": "empty", "normalized_text": "", "warnings": []}

    warnings: List[str] = []
    if use_llm and llm_client and llm_client.enabled:
        try:
            return {
                "requirements": _llm_extract_requirements(normalized, llm_client),
                "method": "llm_top_level_split",
                "normalized_text": normalized,
                "warnings": warnings,
            }
        except Exception as exc:
            warnings.append(f"LLM 切分失败，已回退到规则模式：{exc}")

    return {
        "requirements": _rule_extract_requirements(normalized),
        "method": "rule_fallback",
        "normalized_text": normalized,
        "warnings": warnings,
    }
