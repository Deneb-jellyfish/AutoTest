from __future__ import annotations

import io
import json
from typing import Any, Dict, List

import pandas as pd


def _frame(items: List[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(items if items else [])


def export_project_json(project_state: Dict[str, Any]) -> bytes:
    return json.dumps(project_state, ensure_ascii=False, indent=2).encode("utf-8")


def export_requirements_csv(project_state: Dict[str, Any]) -> bytes:
    frame = _frame(project_state.get("requirements", []))
    return frame.to_csv(index=False).encode("utf-8-sig")


def export_project_excel(project_state: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _frame([project_state.get("project_meta", {})]).to_excel(writer, sheet_name="project_meta", index=False)
        _frame(project_state.get("requirements", [])).to_excel(writer, sheet_name="requirements", index=False)
        _frame(project_state.get("parsed_requirements", [])).to_excel(writer, sheet_name="parsed_requirements", index=False)
        _frame(project_state.get("risk_items", [])).to_excel(writer, sheet_name="risk_items", index=False)
        _frame(project_state.get("coverage_items", [])).to_excel(writer, sheet_name="coverage_items", index=False)
        _frame(project_state.get("strategy_items", [])).to_excel(writer, sheet_name="strategy_items", index=False)
        _frame(project_state.get("audit_log", [])).to_excel(writer, sheet_name="audit_log", index=False)
    return buffer.getvalue()
