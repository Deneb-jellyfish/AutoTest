from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from core.data_model import TestSuite, dataclass_to_dict
from core.state_manager import generate_suite_id


SUITE_TECHNIQUE_LABELS = ["EP", "BVA", "Decision Table", "State Transition"]
TECHNIQUE_LABEL_TO_INTERNAL = {
    "EP": "EP",
    "BVA": "BVA",
    "Decision Table": "DT",
    "State Transition": "ST",
}
TECHNIQUE_INTERNAL_TO_LABEL = {
    "EP": "EP",
    "BVA": "BVA",
    "DT": "Decision Table",
    "ST": "State Transition",
}


def technique_labels_from_internal(items: List[str]) -> List[str]:
    labels: List[str] = []
    for item in items:
        label = TECHNIQUE_INTERNAL_TO_LABEL.get(str(item).strip().upper(), str(item).strip())
        if label and label not in labels:
            labels.append(label)
    return labels


def technique_internal_from_labels(items: List[str]) -> List[str]:
    values: List[str] = []
    for item in items:
        raw = str(item).strip()
        value = TECHNIQUE_LABEL_TO_INTERNAL.get(raw, raw.upper())
        if value and value not in values:
            values.append(value)
    return values


def infer_suite_techniques(ps: Dict[str, Any], requirement_ids: List[str]) -> List[str]:
    labels: List[str] = []
    parsed_map = {item.get("req_id"): item for item in ps.get("parsed_requirements", [])}
    for req_id in requirement_ids:
        parsed_req = parsed_map.get(req_id)
        if not parsed_req:
            continue
        if parsed_req.get("input_fields") and "EP" not in labels:
            labels.append("EP")
        texts = " ".join(
            [
                parsed_req.get("summary", ""),
                " ".join(parsed_req.get("business_rules", [])),
                " ".join(parsed_req.get("ambiguities", [])),
                " ".join(parsed_req.get("conditions", [])),
            ]
        ).lower()
        if any(token in texts for token in ["length", "boundary", "min", "max", "位", "长度"]) and "BVA" not in labels:
            labels.append("BVA")
        if parsed_req.get("conditions") or parsed_req.get("business_rules"):
            if "Decision Table" not in labels:
                labels.append("Decision Table")
        if any(token in texts for token in ["state", "lock", "retry", "status", "状态", "锁定"]):
            if "State Transition" not in labels:
                labels.append("State Transition")

    if not labels:
        labels = ["EP"]
    return labels


def _suite_seed_from_requirement(requirement: Dict[str, Any], parsed_req: Dict[str, Any] | None) -> tuple[str, str]:
    text = " ".join(
        [
            str(requirement.get("title", "")),
            str(requirement.get("raw_text", "")),
            str(parsed_req.get("summary", "") if parsed_req else ""),
        ]
    ).lower()

    if any(token in text for token in ["register", "registration", "signup", "sign up", "注册"]):
        return "registration", "Account Registration Suite"
    if any(token in text for token in ["login", "log in", "signin", "sign in", "登录"]):
        return "login", "Account Login Suite"
    if any(token in text for token in ["security", "lockout", "lock", "attempt", "password", "安全", "锁定"]):
        return "security", "Security and Lockout Suite"
    if any(token in text for token in ["profile", "account", "user"]):
        return "account", "Account Management Suite"
    return "general", "General Regression Suite"


def ensure_default_test_suites(ps: Dict[str, Any]) -> bool:
    changed = False

    if not ps.get("test_suites"):
        parsed_map = {item.get("req_id"): item for item in ps.get("parsed_requirements", []) if item.get("review_status") == "Approved"}
        risk_map = {item.get("req_id"): item for item in ps.get("risk_items", [])}
        grouped_req_ids: dict[str, List[str]] = defaultdict(list)
        grouped_names: dict[str, str] = {}

        for requirement in ps.get("requirements", []):
            req_id = requirement.get("req_id")
            if req_id not in parsed_map:
                continue
            seed_key, suite_name = _suite_seed_from_requirement(requirement, parsed_map.get(req_id))
            grouped_req_ids[seed_key].append(req_id)
            grouped_names[seed_key] = suite_name

        for seed_key, req_ids in grouped_req_ids.items():
            priorities = [risk_map.get(req_id, {}).get("risk_level", "Medium") for req_id in req_ids]
            priority = "High" if "High" in priorities else "Medium" if "Medium" in priorities else "Low"
            suite = dataclass_to_dict(
                TestSuite(
                    suite_id=generate_suite_id(ps),
                    name=grouped_names[seed_key],
                    priority=priority,
                    requirement_ids=req_ids,
                    selected_techniques=technique_internal_from_labels(infer_suite_techniques(ps, req_ids)),
                    notes="Auto-suggested from approved requirements and risk context.",
                    last_edited_by="system",
                )
            )
            ps["test_suites"].append(suite)
        changed = bool(ps.get("test_suites"))

    requirement_ids_in_suites = {
        req_id
        for suite in ps.get("test_suites", [])
        for req_id in suite.get("requirement_ids", [])
    }
    approved_req_ids = [
        item.get("req_id")
        for item in ps.get("parsed_requirements", [])
        if item.get("review_status") == "Approved"
    ]
    missing_req_ids = [req_id for req_id in approved_req_ids if req_id and req_id not in requirement_ids_in_suites]
    if missing_req_ids:
        fallback_suite = next((item for item in ps["test_suites"] if item.get("name") == "General Regression Suite"), None)
        if fallback_suite is None:
            fallback_suite = dataclass_to_dict(
                TestSuite(
                    suite_id=generate_suite_id(ps),
                    name="General Regression Suite",
                    priority="Medium",
                    requirement_ids=[],
                    selected_techniques=["EP"],
                    notes="Fallback suite for uncovered approved requirements.",
                    last_edited_by="system",
                )
            )
            ps["test_suites"].append(fallback_suite)
        fallback_suite["requirement_ids"] = sorted(set(fallback_suite.get("requirement_ids", []) + missing_req_ids))
        fallback_suite["selected_techniques"] = technique_internal_from_labels(infer_suite_techniques(ps, fallback_suite["requirement_ids"]))
        changed = True

    return changed


def sync_coverage_suite_ids(ps: Dict[str, Any]) -> bool:
    changed = False
    suite_map = {suite.get("suite_id"): suite for suite in ps.get("test_suites", [])}

    for coverage_item in ps.get("coverage_items", []):
        req_id = coverage_item.get("req_id")
        desired_suite_ids = [
            suite_id
            for suite_id, suite in suite_map.items()
            if req_id in suite.get("requirement_ids", [])
        ]
        if not coverage_item.get("suite_ids") and desired_suite_ids:
            coverage_item["suite_ids"] = desired_suite_ids
            changed = True
    return changed


def suite_counts(ps: Dict[str, Any], suite_id: str) -> Dict[str, int]:
    suite_coverage = [item for item in ps.get("coverage_items", []) if suite_id in item.get("suite_ids", [])]
    suite_cases = [item for item in ps.get("test_cases", []) if suite_id in item.get("suite_ids", [])]
    return {
        "coverage_count": len(suite_coverage),
        "confirmed_coverage_count": len([item for item in suite_coverage if item.get("review_status") == "Confirmed"]),
        "test_case_count": len(suite_cases),
    }


def coverage_progress_by_suite(ps: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for suite in ps.get("test_suites", []):
        counts = suite_counts(ps, suite.get("suite_id", ""))
        rows.append(
            {
                "suite_id": suite.get("suite_id", ""),
                "suite_name": suite.get("name", ""),
                "priority": suite.get("priority", "Medium"),
                "assigned_coverage_count": counts["coverage_count"],
                "confirmed_coverage_count": counts["confirmed_coverage_count"],
                "test_case_count": counts["test_case_count"],
            }
        )
    return rows


def assign_suite_ids_to_test_case(test_case: Dict[str, Any], coverage_item: Dict[str, Any] | None) -> None:
    if coverage_item is None:
        test_case.setdefault("suite_ids", [])
        return
    test_case["suite_ids"] = list(coverage_item.get("suite_ids", []))
