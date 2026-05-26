from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from core.data_model import empty_project_state


EXPORT_DIR = Path("exports")


def _normalize_cell(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _normalize_records(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append({key: _normalize_cell(value) for key, value in item.items()})
    return rows


def _frame(items: List[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(_normalize_records(items) if items else [])


def _internal_from_export_state(data: Dict[str, Any]) -> Dict[str, Any]:
    if "project_meta" in data:
        return data

    mapped = empty_project_state()
    mapped["project_meta"] = data.get("project_info", mapped["project_meta"])
    mapped["requirements"] = data.get("requirements", [])
    mapped["parsed_requirements"] = data.get("structured_requirements", [])
    mapped["coverage_items"] = data.get("coverage_items", [])
    mapped["risk_items"] = data.get("risk_items", [])
    mapped["test_suites"] = data.get("test_suites", [])
    mapped["strategy_items"] = data.get("strategy_items", [])
    mapped["test_cases"] = data.get("test_cases", [])
    mapped["traceability_matrix"] = data.get("traceability_matrix", [])
    mapped["audit_log"] = data.get("change_log", [])
    return mapped


def ensure_project_state(project_state: Dict[str, Any]) -> Dict[str, Any]:
    source = _internal_from_export_state(project_state)
    canonical = {
        "project_info": source.get("project_meta", {}),
        "requirements": source.get("requirements", []),
        "structured_requirements": source.get("parsed_requirements", []),
        "coverage_items": source.get("coverage_items", []),
        "risk_items": source.get("risk_items", []),
        "test_suites": source.get("test_suites", []),
        "strategy_items": source.get("strategy_items", []),
        "test_cases": source.get("test_cases", []),
        "traceability_matrix": source.get("traceability_matrix", []),
        "change_log": source.get("audit_log", []),
    }
    return canonical


def export_to_json(project_state: Dict[str, Any]) -> bytes:
    return json.dumps(ensure_project_state(project_state), ensure_ascii=False, indent=2).encode("utf-8")


def export_to_csv_bundle(project_state: Dict[str, Any]) -> bytes:
    state = ensure_project_state(project_state)
    files = {
        "project_info.csv": _frame([state.get("project_info", {})]).to_csv(index=False).encode("utf-8-sig"),
        "requirements.csv": _frame(state.get("requirements", [])).to_csv(index=False).encode("utf-8-sig"),
        "structured_requirements.csv": _frame(state.get("structured_requirements", [])).to_csv(index=False).encode("utf-8-sig"),
        "coverage_items.csv": _frame(state.get("coverage_items", [])).to_csv(index=False).encode("utf-8-sig"),
        "risk_items.csv": _frame(state.get("risk_items", [])).to_csv(index=False).encode("utf-8-sig"),
        "test_suites.csv": _frame(state.get("test_suites", [])).to_csv(index=False).encode("utf-8-sig"),
        "strategy_items.csv": _frame(state.get("strategy_items", [])).to_csv(index=False).encode("utf-8-sig"),
        "test_cases.csv": _frame(state.get("test_cases", [])).to_csv(index=False).encode("utf-8-sig"),
        "traceability_matrix.csv": _frame(state.get("traceability_matrix", [])).to_csv(index=False).encode("utf-8-sig"),
        "change_log.csv": _frame(state.get("change_log", [])).to_csv(index=False).encode("utf-8-sig"),
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def export_to_excel(project_state: Dict[str, Any]) -> bytes:
    state = ensure_project_state(project_state)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _frame([state.get("project_info", {})]).to_excel(writer, sheet_name="ProjectInfo", index=False)
        _frame(state.get("requirements", [])).to_excel(writer, sheet_name="Requirements", index=False)
        _frame(state.get("structured_requirements", [])).to_excel(writer, sheet_name="StructuredRequirements", index=False)
        _frame(state.get("coverage_items", [])).to_excel(writer, sheet_name="CoverageItems", index=False)
        _frame(state.get("risk_items", [])).to_excel(writer, sheet_name="RiskItems", index=False)
        _frame(state.get("test_suites", [])).to_excel(writer, sheet_name="TestSuites", index=False)
        _frame(state.get("strategy_items", [])).to_excel(writer, sheet_name="StrategyItems", index=False)
        _frame(state.get("test_cases", [])).to_excel(writer, sheet_name="TestCases", index=False)
        _frame(state.get("traceability_matrix", [])).to_excel(writer, sheet_name="TraceabilityMatrix", index=False)
        _frame(state.get("change_log", [])).to_excel(writer, sheet_name="ChangeLog", index=False)
    return buffer.getvalue()


def save_export_file(filename: str, content: bytes) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / filename
    path.write_bytes(content)
    return path


def load_project_from_json_bytes(content: bytes) -> Dict[str, Any]:
    data = json.loads(content.decode("utf-8"))
    return _internal_from_export_state(data)
