from __future__ import annotations

from typing import Any, Dict

from core.llm_client import LlmClient
from utils.prompt_templates import RISK_SCORING_PROMPT


def score_risk(req_text: str, llm: LlmClient) -> Dict[str, Any]:
    return llm.json_completion(RISK_SCORING_PROMPT, req_text)
