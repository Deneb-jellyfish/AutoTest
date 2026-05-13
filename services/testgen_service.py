from __future__ import annotations

import json
from typing import Any, Dict, List

from core.llm_client import LlmClient
from utils.prompt_templates import TESTCASE_GEN_BATCH_PROMPT, TESTCASE_GEN_PROMPT


def generate_test_cases(requirements: List[Dict[str, Any]], llm: LlmClient) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for req in requirements:
        cases = llm.json_list_completion(TESTCASE_GEN_PROMPT, req["raw_text"])
        for i, c in enumerate(cases, start=1):
            c.setdefault("tc_id", f"TC-{req['id']}-{i:03d}")
            c.setdefault("req_id", req["id"])
            c.setdefault("priority", req.get("risk", {}).get("level", "Medium"))
            c["ai_generated"] = True
            c["user_modified"] = False
            c["version"] = 1
        out.extend(cases)
    return out


def batch_generate_test_cases(requirements: List[Dict[str, Any]], llm: LlmClient, batch_size: int = 5) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    payload_items = []
    for r in requirements:
        payload_items.append(
            {
                "id": r["id"],
                "text": r["raw_text"],
                "risk_level": (r.get("risk", {}) or {}).get("level", "Medium"),
            }
        )

    for start in range(0, len(payload_items), batch_size):
        batch = payload_items[start : start + batch_size]
        payload = json.dumps({"requirements": batch}, ensure_ascii=False)
        cases = llm.json_any_completion(TESTCASE_GEN_BATCH_PROMPT, payload)
        if not isinstance(cases, list):
            raise ValueError("Expected a JSON array response for batch test generation.")
        for c in cases:
            if not isinstance(c, dict):
                continue
            out.append(c)

    # Normalize required fields and fill defaults
    by_req_counter: dict[str, int] = {}
    for c in out:
        req_id = str(c.get("req_id", "")).strip()
        if not req_id:
            continue
        by_req_counter.setdefault(req_id, 0)
        by_req_counter[req_id] += 1
        c.setdefault("tc_id", f"TC-{req_id}-{by_req_counter[req_id]:03d}")
        c.setdefault("priority", "Medium")
        c["ai_generated"] = True
        c["user_modified"] = False
        c["version"] = 1

    return out
