from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import streamlit as st

from core.data_model import empty_project_state, utc_now_iso
from utils.persistence import load_from_db, save_to_db


PROJECT_STATE_KEY = "project_state"


def _normalize_loaded_state(ps: Dict[str, Any]) -> Dict[str, Any]:
    for req in ps.get("requirements", []):
        req_id = req.get("requirement_id") or req.get("req_id")
        if not req_id:
            continue
        req["requirement_id"] = req_id
        req["req_id"] = req_id
        req.setdefault("source_annotations", [{"text": str(req.get("raw_text", ""))[:80], "category": "source"}])
        req.setdefault("review_status", "Imported")
        req.setdefault("tags", [])
        req.setdefault("notes", "")

    for parsed in ps.get("parsed_requirements", []):
        req_id = parsed.get("requirement_id") or parsed.get("req_id")
        if req_id:
            parsed["requirement_id"] = req_id
            parsed["req_id"] = req_id
        parsed.setdefault("summary", "")
        parsed.setdefault("actor", parsed.get("who", ""))
        parsed.setdefault("action", parsed.get("what", ""))
        parsed.setdefault("expected_action", "")
        parsed.setdefault("object_under_test", "")
        parsed.setdefault("trigger", "")
        parsed.setdefault("business_rules", parsed.get("constraints", []))
        parsed.setdefault("preconditions", [])
        parsed.setdefault("expected_result", parsed.get("expected_outcomes", []))
        parsed.setdefault("error_handling", [])
        parsed.setdefault("assumptions", [])
        parsed.setdefault("source_annotations", parsed.get("evidence_annotations", []))
        parsed.setdefault("rationale", "")
        parsed.setdefault("review_status", "Proposed")
    return ps


def _ensure_meta(ps: Dict[str, Any]) -> Dict[str, Any]:
    defaults = empty_project_state()
    for key, value in defaults.items():
        ps.setdefault(key, value if not isinstance(value, list) else list(value))

    meta = ps.setdefault("project_meta", {})
    meta.setdefault("project_name", "AutoTestDesign Project")
    meta.setdefault("target_app", "To-Do List Web Application")
    meta.setdefault("created_at", utc_now_iso())
    meta["last_modified"] = meta.get("last_modified") or utc_now_iso()
    return _normalize_loaded_state(ps)


def get_state() -> Dict[str, Any]:
    if PROJECT_STATE_KEY not in st.session_state:
        loaded = load_from_db()
        st.session_state[PROJECT_STATE_KEY] = _ensure_meta(loaded or empty_project_state())
    return _ensure_meta(st.session_state[PROJECT_STATE_KEY])


def set_state(ps: Dict[str, Any]) -> None:
    st.session_state[PROJECT_STATE_KEY] = _ensure_meta(ps)
    save_to_db(st.session_state[PROJECT_STATE_KEY])


def save_state(ps: Dict[str, Any]) -> None:
    ps = _ensure_meta(ps)
    ps["project_meta"]["last_modified"] = utc_now_iso()
    st.session_state[PROJECT_STATE_KEY] = ps
    save_to_db(ps)


def reset_state() -> Dict[str, Any]:
    fresh = empty_project_state()
    set_state(fresh)
    return fresh


def generate_next_id(items: Iterable[Dict[str, Any]], field_name: str, prefix: str) -> str:
    numbers = []
    for item in items:
        raw_value = str(item.get(field_name, ""))
        if raw_value.startswith(f"{prefix}-"):
            suffix = raw_value.split("-", 1)[1]
            if suffix.isdigit():
                numbers.append(int(suffix))
    next_num = max(numbers, default=0) + 1
    return f"{prefix}-{next_num:03d}"


def generate_requirement_id(ps: Dict[str, Any]) -> str:
    return generate_next_id(ps["requirements"], "req_id", "REQ")


def generate_parsed_id(ps: Dict[str, Any]) -> str:
    return generate_next_id(ps["parsed_requirements"], "parsed_id", "PR")


def generate_risk_id(ps: Dict[str, Any]) -> str:
    return generate_next_id(ps["risk_items"], "risk_id", "RISK")


def generate_coverage_id(ps: Dict[str, Any]) -> str:
    return generate_next_id(ps["coverage_items"], "cov_id", "COV")


def generate_strategy_id(ps: Dict[str, Any]) -> str:
    return generate_next_id(ps["strategy_items"], "strategy_id", "STR")


def find_by_id(items: Iterable[Dict[str, Any]], field_name: str, object_id: str) -> Optional[Dict[str, Any]]:
    for item in items:
        if item.get(field_name) == object_id:
            return item
    return None


def find_requirement(ps: Dict[str, Any], req_id: str) -> Optional[Dict[str, Any]]:
    return find_by_id(ps["requirements"], "req_id", req_id)


def find_parsed_by_req_id(ps: Dict[str, Any], req_id: str) -> Optional[Dict[str, Any]]:
    return find_by_id(ps["parsed_requirements"], "req_id", req_id)


def find_parsed(ps: Dict[str, Any], parsed_id: str) -> Optional[Dict[str, Any]]:
    return find_by_id(ps["parsed_requirements"], "parsed_id", parsed_id)


def find_risk_by_req_id(ps: Dict[str, Any], req_id: str) -> Optional[Dict[str, Any]]:
    return find_by_id(ps["risk_items"], "req_id", req_id)


def find_risk(ps: Dict[str, Any], risk_id: str) -> Optional[Dict[str, Any]]:
    return find_by_id(ps["risk_items"], "risk_id", risk_id)


def find_coverage(ps: Dict[str, Any], cov_id: str) -> Optional[Dict[str, Any]]:
    return find_by_id(ps["coverage_items"], "cov_id", cov_id)


def find_strategy_by_cov(ps: Dict[str, Any], cov_id: str) -> Optional[Dict[str, Any]]:
    return find_by_id(ps["strategy_items"], "cov_id", cov_id)
