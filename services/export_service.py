from __future__ import annotations

import io
import json
from typing import Any, Dict, List

import pandas as pd


def export_json(requirements: List[Dict[str, Any]], test_cases: List[Dict[str, Any]]) -> bytes:
    payload = {"requirements": requirements, "test_cases": test_cases}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def export_excel(requirements: List[Dict[str, Any]], test_cases: List[Dict[str, Any]]) -> bytes:
    req_rows = []
    for r in requirements:
        req_rows.append(
            {
                "req_id": r.get("id"),
                "raw_text": r.get("raw_text"),
                "risk_score": r.get("risk", {}).get("score"),
                "risk_level": r.get("risk", {}).get("level"),
                "input_fields": ", ".join(r.get("parsed", {}).get("input_fields", []) or []),
                "data_ranges": ", ".join(r.get("parsed", {}).get("data_ranges", []) or []),
                "conditions": " | ".join(r.get("parsed", {}).get("conditions", []) or []),
                "expected_actions": " | ".join(r.get("parsed", {}).get("expected_actions", []) or []),
                "modified_by_user": bool(r.get("modified_by_user", False)),
            }
        )
    tc_rows = []
    for tc in test_cases:
        tc_rows.append({k: tc.get(k) for k in ["tc_id", "req_id", "technique", "coverage_item", "condition", "input_data", "expected", "priority", "ai_generated", "user_modified", "version"]})

    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        pd.DataFrame(req_rows).to_excel(writer, index=False, sheet_name="Requirements")
        pd.DataFrame(tc_rows).to_excel(writer, index=False, sheet_name="TestCases")
    return bio.getvalue()

