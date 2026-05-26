from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List


RAW_REQUIREMENT_STATUS = ["Draft", "Imported", "Modified", "Structured", "Archived"]
STRUCTURED_REVIEW_STATUS = ["Proposed", "Modified", "Approved", "Rejected", "Need Clarification"]
RECORD_REVIEW_STATUS = ["Draft", "Modified", "Confirmed", "Rejected", "Needs Discussion"]
TEST_CASE_REVIEW_STATUS = ["Proposed", "Modified", "Approved", "Rejected", "Need Clarification"]
TEST_CASE_STATUS = ["Draft", "Ready", "Blocked", "Deprecated"]
EXECUTION_TYPES = ["Manual", "Automated"]
PRIORITY_LEVELS = ["High", "Medium", "Low"]
RISK_LEVELS = ["High", "Medium", "Low"]
COVERAGE_CATEGORIES = ["Input", "Boundary", "Logic", "State", "Error", "Performance", "UI"]
TECHNIQUES = ["EP", "BVA", "DT", "ST"]


@dataclass
class Requirement:
    requirement_id: str
    req_id: str
    title: str
    raw_text: str
    source: str
    priority: str
    review_status: str
    source_annotations: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = ""


@dataclass
class ParsedRequirement:
    parsed_id: str
    requirement_id: str
    req_id: str
    summary: str = ""
    actor: str = ""
    action: str = ""
    expected_action: str = ""
    object_under_test: str = ""
    trigger: str = ""
    input_fields: List[Dict[str, Any]] = field(default_factory=list)
    business_rules: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    expected_result: List[str] = field(default_factory=list)
    error_handling: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    source_annotations: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    review_status: str = "Proposed"
    last_edited_by: str = "llm"
    edit_history: List[Dict[str, Any]] = field(default_factory=list)
    who: str = ""
    what: str = ""
    constraints: List[str] = field(default_factory=list)
    expected_outcomes: List[str] = field(default_factory=list)
    system_behaviors: List[str] = field(default_factory=list)
    evidence_annotations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RiskItem:
    risk_id: str
    req_id: str
    parsed_id: str
    risk_title: str
    risk_summary: str
    impact: int
    likelihood: int
    complexity: int
    usage_frequency: int
    risk_score: int
    risk_level: str
    rationale: str
    evidence_keywords: List[str] = field(default_factory=list)
    mitigation_hint: str = ""
    review_status: str = "Draft"
    last_edited_by: str = "llm"


@dataclass
class CoverageItem:
    cov_id: str
    req_id: str
    parsed_id: str
    risk_id: str
    category: str
    title: str
    description: str
    test_focus: str
    input_partitions: List[str] = field(default_factory=list)
    boundary_values: List[str] = field(default_factory=list)
    suggested_technique: str = "EP"
    risk_level: str = "Medium"
    review_status: str = "Draft"
    last_edited_by: str = "llm"
    suite_ids: List[str] = field(default_factory=list)


@dataclass
class StrategyItem:
    strategy_id: str
    req_id: str
    cov_id: str
    risk_id: str
    recommended_technique: str
    selected_technique: str
    technique_rationale: str
    generation_notes: str
    review_status: str = "Draft"


@dataclass
class TestSuite:
    suite_id: str
    name: str
    priority: str = "Medium"
    requirement_ids: List[str] = field(default_factory=list)
    selected_techniques: List[str] = field(default_factory=list)
    notes: str = ""
    last_edited_by: str = "system"


@dataclass
class AuditEntry:
    log_id: str
    timestamp: str
    object_type: str
    object_id: str
    action: str
    changed_field: str
    old_value: str | None
    new_value: str | None
    changed_by: str
    reason: str


@dataclass
class TestCase:
    test_case_id: str
    requirement_id: str
    coverage_id: str
    strategy_id: str
    title: str
    objective: str
    technique: str
    suite_ids: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    test_data: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)
    expected_result: List[str] = field(default_factory=list)
    priority: str = "Medium"
    execution_type: str = "Manual"
    status: str = "Not Run"
    review_status: str = "Proposed"
    last_edited_by: str = "rule"
    source_coverage_title: str = ""
    source_strategy_notes: str = ""


def utc_now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def empty_project_state() -> Dict[str, Any]:
    now = utc_now_iso()
    return {
        "project_meta": {
            "project_name": "AutoTestDesign Project",
            "target_app": "To-Do List Web Application",
            "created_at": now,
            "last_modified": now,
        },
        "requirements": [],
        "parsed_requirements": [],
        "risk_items": [],
        "test_suites": [],
        "coverage_items": [],
        "strategy_items": [],
        "test_cases": [],
        "traceability_matrix": [],
        "audit_log": [],
    }


def dataclass_to_dict(model: Any) -> Dict[str, Any]:
    return asdict(model)
