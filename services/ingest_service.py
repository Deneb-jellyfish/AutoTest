from __future__ import annotations

import json
from typing import Any, Dict

from core.llm_client import LlmClient
from utils.prompt_templates import STRUCTURE_AND_RISK_BATCH_PROMPT, STRUCTURE_AND_RISK_PROMPT


def parse_and_score(req_text: str, llm: LlmClient) -> Dict[str, Any]:
    data = llm.json_completion(STRUCTURE_AND_RISK_PROMPT, req_text)
    parsed = data.get("parsed") or {}
    risk = data.get("risk") or {}
    if not isinstance(parsed, dict) or not isinstance(risk, dict):
        raise ValueError("LLM response missing 'parsed' or 'risk'.")
    return {"parsed": parsed, "risk": risk}


def batch_parse_and_score(requirements: list[dict[str, str]], llm: LlmClient) -> list[dict[str, Any]]:
    """
    requirements: [{"id": "...", "text": "..."}, ...]
    returns: [{"id": "...", "parsed": {...}, "risk": {...}}, ...] in the same order
    """
    payload = json.dumps({"requirements": requirements}, ensure_ascii=False)
    data = llm.json_any_completion(STRUCTURE_AND_RISK_BATCH_PROMPT, payload)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array response for batch parse.")
    return [x for x in data if isinstance(x, dict)]
