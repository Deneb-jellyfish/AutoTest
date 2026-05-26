from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from core.data_model import TestCase, dataclass_to_dict
from core.llm_client import LlmClient


TEST_CASE_SYSTEM_PROMPT = """
你是一名专业的软件测试设计工程师。
请根据提供的结构化需求、风险、覆盖项和策略项，生成测试用例。

严格返回 JSON：
{
  "test_cases": [
    {
      "coverage_id": "关联 coverage id",
      "strategy_id": "关联 strategy id",
      "title": "测试用例标题",
      "objective": "测试目标",
      "technique": "EP|BVA|DT|ST",
      "preconditions": ["前置条件1"],
      "test_data": {"field": "value"},
      "steps": ["步骤1", "步骤2"],
      "expected_result": ["预期结果1"],
      "priority": "High|Medium|Low"
    }
  ]
}

要求：
- 每个 strategy item 至少生成 3 条测试用例
- 每条用例必须带 coverage_id 和 strategy_id
- 不要返回任何额外说明文字
"""


def _technique_key(value: str) -> str:
    raw = (value or "").strip().upper()
    if raw in {"DT", "DECISION TABLE", "DECISION_TABLE"}:
        return "DT"
    if raw in {"ST", "STATE TRANSITION", "STATE_TRANSITION"}:
        return "ST"
    if raw in {"BVA", "BOUNDARY VALUE", "BOUNDARY_VALUE"}:
        return "BVA"
    return "EP"


def _priority_from_risk(risk_item: Dict[str, Any], coverage_item: Dict[str, Any]) -> str:
    level = str(risk_item.get("risk_level") or coverage_item.get("risk_level") or "Medium").strip().title()
    return level if level in {"High", "Medium", "Low"} else "Medium"


def _default_valid_value(field_name: str, field_type: str = "string") -> Any:
    name = field_name.lower()
    if "email" in name:
        return "user@example.com"
    if "password" in name or "pwd" in name:
        return "CorrectPass123"
    if "title" in name or "name" in name:
        return "Valid task title"
    if "status" in name:
        return "active"
    if "count" in name or "num" in name or "quantity" in name:
        return 10
    if field_type == "number":
        return 1
    if field_type == "boolean":
        return True
    return "valid_value"


def _default_invalid_value(field_name: str, field_type: str = "string") -> Any:
    name = field_name.lower()
    if "email" in name:
        return "invalid-email"
    if "password" in name or "pwd" in name:
        return "wrong"
    if "title" in name or "name" in name:
        return ""
    if "count" in name or "num" in name or "quantity" in name:
        return -1
    if field_type == "number":
        return -1
    if field_type == "boolean":
        return False
    return ""


def _base_test_data(parsed_req: Dict[str, Any]) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for field in parsed_req.get("input_fields", []):
        name = str(field.get("name", "")).strip()
        if not name:
            continue
        data[name] = _default_valid_value(name, str(field.get("type", "string")).strip().lower())
    return data


def _choose_target_field(coverage_item: Dict[str, Any], parsed_req: Dict[str, Any]) -> Tuple[str, str]:
    title_text = f"{coverage_item.get('title', '')} {coverage_item.get('description', '')}".lower()
    input_fields = parsed_req.get("input_fields", [])
    for field in input_fields:
        name = str(field.get("name", "")).strip()
        field_type = str(field.get("type", "string")).strip().lower()
        if name and name.lower() in title_text:
            return name, field_type
    for preferred in ("email", "password", "title", "task_title", "name"):
        for field in input_fields:
            name = str(field.get("name", "")).strip()
            field_type = str(field.get("type", "string")).strip().lower()
            if preferred in name.lower():
                return name, field_type
    if input_fields:
        field = input_fields[0]
        return str(field.get("name", "input")).strip() or "input", str(field.get("type", "string")).strip().lower()
    return "input", "string"


def _extract_range(*texts: str) -> Tuple[int, int]:
    joined = " ".join(texts)
    match = re.search(r"(\d+)\D{0,8}(?:to|~|-|到|至)\D{0,8}(\d+)", joined, flags=re.IGNORECASE)
    if match:
        low, high = int(match.group(1)), int(match.group(2))
        if low <= high:
            return low, high
    numbers = [int(value) for value in re.findall(r"\d+", joined)]
    if len(numbers) >= 2:
        low, high = min(numbers[0], numbers[1]), max(numbers[0], numbers[1])
        return low, high
    return 8, 20


def _make_test_case(
    test_case_id: str,
    requirement_id: str,
    coverage_item: Dict[str, Any],
    strategy_item: Dict[str, Any],
    risk_item: Dict[str, Any],
    payload: Dict[str, Any],
    last_edited_by: str,
) -> Dict[str, Any]:
    return dataclass_to_dict(
        TestCase(
            test_case_id=test_case_id,
            requirement_id=requirement_id,
            coverage_id=coverage_item["cov_id"],
            strategy_id=strategy_item["strategy_id"],
            title=str(payload.get("title", "")).strip(),
            objective=str(payload.get("objective", "")).strip(),
            technique=_technique_key(str(payload.get("technique") or strategy_item.get("selected_technique") or coverage_item.get("suggested_technique") or "EP")),
            suite_ids=list(coverage_item.get("suite_ids", [])),
            preconditions=[str(item).strip() for item in payload.get("preconditions", []) if str(item).strip()],
            test_data=payload.get("test_data", {}) if isinstance(payload.get("test_data", {}), dict) else {},
            steps=[str(item).strip() for item in payload.get("steps", []) if str(item).strip()],
            expected_result=[str(item).strip() for item in payload.get("expected_result", []) if str(item).strip()],
            priority=str(payload.get("priority") or _priority_from_risk(risk_item, coverage_item)).title(),
            execution_type="Manual",
            status="Not Run",
            review_status="Proposed",
            last_edited_by=last_edited_by,
            source_coverage_title=coverage_item.get("title", ""),
            source_strategy_notes=strategy_item.get("generation_notes", ""),
        )
    )


def _next_test_case_id(existing_cases: List[Dict[str, Any]], pending_cases: List[Dict[str, Any]]) -> str:
    max_num = 0
    for item in [*existing_cases, *pending_cases]:
        raw = str(item.get("test_case_id", ""))
        if raw.startswith("TC-"):
            suffix = raw.split("-", 1)[1]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"TC-{max_num + 1:03d}"


def _generate_ep_cases(parsed_req: Dict[str, Any], coverage_item: Dict[str, Any], strategy_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    base_data = _base_test_data(parsed_req)
    field_name, field_type = _choose_target_field(coverage_item, parsed_req)
    valid_data = deepcopy(base_data)
    valid_data[field_name] = _default_valid_value(field_name, field_type)

    invalid_data = deepcopy(base_data)
    invalid_data[field_name] = _default_invalid_value(field_name, field_type)

    empty_data = deepcopy(base_data)
    empty_data[field_name] = ""

    objective_prefix = coverage_item.get("test_focus") or coverage_item.get("description") or coverage_item.get("title", "")

    return [
        {
            "title": f"{coverage_item['title']} - valid partition",
            "objective": f"Validate accepted input for {objective_prefix}",
            "technique": "EP",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": valid_data,
            "steps": ["Open the target workflow.", f"Enter a valid value into `{field_name}`.", "Submit the action."],
            "expected_result": parsed_req.get("expected_result", []) or ["The request is accepted successfully."],
        },
        {
            "title": f"{coverage_item['title']} - invalid partition",
            "objective": f"Validate rejection of invalid input for {objective_prefix}",
            "technique": "EP",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": invalid_data,
            "steps": ["Open the target workflow.", f"Enter an invalid value into `{field_name}`.", "Submit the action."],
            "expected_result": parsed_req.get("error_handling", []) or ["The system rejects the request and shows an error."],
        },
        {
            "title": f"{coverage_item['title']} - empty partition",
            "objective": f"Validate required-field handling for {objective_prefix}",
            "technique": "EP",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": empty_data,
            "steps": ["Open the target workflow.", f"Leave `{field_name}` empty.", "Submit the action."],
            "expected_result": parsed_req.get("error_handling", []) or ["The system blocks submission and shows a required-field message."],
        },
    ]


def _generate_bva_cases(parsed_req: Dict[str, Any], coverage_item: Dict[str, Any], strategy_item: Dict[str, Any], risk_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    low, high = _extract_range(
        coverage_item.get("description", ""),
        coverage_item.get("title", ""),
        strategy_item.get("generation_notes", ""),
        risk_item.get("mitigation_hint", ""),
        " ".join(parsed_req.get("business_rules", [])),
    )
    field_name, field_type = _choose_target_field(coverage_item, parsed_req)
    base_data = _base_test_data(parsed_req)

    def payload(value: Any) -> Dict[str, Any]:
        data = deepcopy(base_data)
        data[field_name] = value
        return data

    return [
        {
            "title": f"{coverage_item['title']} - below minimum",
            "objective": "Validate lower-bound rejection.",
            "technique": "BVA",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": payload(max(low - 1, 0) if field_type == "number" else "x" * max(low - 1, 0)),
            "steps": ["Open the target workflow.", f"Enter a value below the minimum boundary for `{field_name}`.", "Submit the action."],
            "expected_result": parsed_req.get("error_handling", []) or ["The system rejects the value below the minimum boundary."],
        },
        {
            "title": f"{coverage_item['title']} - minimum",
            "objective": "Validate the exact minimum boundary.",
            "technique": "BVA",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": payload(low if field_type == "number" else "x" * max(low, 1)),
            "steps": ["Open the target workflow.", f"Enter the exact minimum boundary for `{field_name}`.", "Submit the action."],
            "expected_result": parsed_req.get("expected_result", []) or ["The system accepts the minimum boundary value."],
        },
        {
            "title": f"{coverage_item['title']} - maximum",
            "objective": "Validate the exact maximum boundary.",
            "technique": "BVA",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": payload(high if field_type == "number" else "x" * max(high, 1)),
            "steps": ["Open the target workflow.", f"Enter the exact maximum boundary for `{field_name}`.", "Submit the action."],
            "expected_result": parsed_req.get("expected_result", []) or ["The system accepts the maximum boundary value."],
        },
        {
            "title": f"{coverage_item['title']} - above maximum",
            "objective": "Validate upper-bound rejection.",
            "technique": "BVA",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": payload(high + 1 if field_type == "number" else "x" * (high + 1)),
            "steps": ["Open the target workflow.", f"Enter a value above the maximum boundary for `{field_name}`.", "Submit the action."],
            "expected_result": parsed_req.get("error_handling", []) or ["The system rejects the value above the maximum boundary."],
        },
    ]


def _generate_decision_table_cases(parsed_req: Dict[str, Any], coverage_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    ambiguous = "ambigu" in coverage_item.get("title", "").lower() or "clarif" in coverage_item.get("title", "").lower()
    if ambiguous:
        cases = [
            ("Clarification path - interpretation A", "Apply interpretation A and verify the observed result."),
            ("Clarification path - interpretation B", "Apply interpretation B and verify the observed result."),
            ("Clarification path - unresolved", "Leave the ambiguity unresolved and verify the product flags the uncertainty."),
        ]
    else:
        cases = [
            ("Valid combination", "Provide a fully valid condition combination."),
            ("Partially invalid combination", "Provide one invalid condition in the combination."),
            ("System-blocking combination", "Provide a combination that should be rejected or blocked."),
            ("Exceptional combination", "Provide a special business-rule combination and verify system behavior."),
        ]

    output = []
    for title_suffix, objective in cases:
        output.append(
            {
                "title": f"{coverage_item['title']} - {title_suffix}",
                "objective": objective,
                "technique": "DT",
                "preconditions": parsed_req.get("preconditions", []),
                "test_data": _base_test_data(parsed_req),
                "steps": ["Prepare the condition combination.", "Perform the target action.", "Observe the resulting decision and response."],
                "expected_result": parsed_req.get("expected_result", []) or ["The system outcome matches the expected business decision."],
            }
        )
    return output


def _generate_state_transition_cases(parsed_req: Dict[str, Any], coverage_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "title": f"{coverage_item['title']} - below threshold state",
            "objective": "Validate behavior before the transition threshold is reached.",
            "technique": "ST",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": _base_test_data(parsed_req),
            "steps": ["Prepare the entity in the initial state.", "Perform the transition-driving action below the threshold.", "Observe the current state."],
            "expected_result": ["The entity remains in the original state and no transition occurs."],
        },
        {
            "title": f"{coverage_item['title']} - threshold transition",
            "objective": "Validate the exact point where the state transition occurs.",
            "technique": "ST",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": _base_test_data(parsed_req),
            "steps": ["Prepare the entity close to the transition threshold.", "Perform the action that reaches the threshold.", "Observe the new state."],
            "expected_result": parsed_req.get("expected_result", []) or ["The entity transitions to the expected next state."],
        },
        {
            "title": f"{coverage_item['title']} - post-lock attempt",
            "objective": "Validate behavior after the terminal or locked state has been reached.",
            "technique": "ST",
            "preconditions": parsed_req.get("preconditions", []),
            "test_data": _base_test_data(parsed_req),
            "steps": ["Prepare the entity in the terminal or locked state.", "Attempt the same action again.", "Observe the system response."],
            "expected_result": ["The system blocks the action or keeps the entity in the locked state with the correct feedback."],
        },
    ]


def _generate_for_strategy(parsed_req: Dict[str, Any], coverage_item: Dict[str, Any], strategy_item: Dict[str, Any], risk_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    technique = _technique_key(str(strategy_item.get("selected_technique") or strategy_item.get("recommended_technique") or coverage_item.get("suggested_technique") or "EP"))
    if technique == "BVA":
        return _generate_bva_cases(parsed_req, coverage_item, strategy_item, risk_item)
    if technique == "DT":
        return _generate_decision_table_cases(parsed_req, coverage_item)
    if technique == "ST":
        return _generate_state_transition_cases(parsed_req, coverage_item)
    return _generate_ep_cases(parsed_req, coverage_item, strategy_item)


def _generate_llm_cases(
    existing_cases: List[Dict[str, Any]],
    requirement: Dict[str, Any],
    parsed_req: Dict[str, Any],
    coverage_items: List[Dict[str, Any]],
    risk_item: Dict[str, Any],
    strategy_items: List[Dict[str, Any]],
    llm_client: LlmClient,
) -> List[Dict[str, Any]]:
    coverage_map = {item["cov_id"]: item for item in coverage_items}
    payload = {
        "requirement": requirement,
        "structured_requirement": parsed_req,
        "risk": risk_item,
        "coverage_items": coverage_items,
        "strategy_items": strategy_items,
    }
    response = llm_client.json_completion(TEST_CASE_SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False))
    items = response.get("test_cases", [])
    if not isinstance(items, list):
        raise ValueError("LLM response missing test_cases list.")

    generated: List[Dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        coverage_id = str(row.get("coverage_id", "")).strip()
        strategy_id = str(row.get("strategy_id", "")).strip()
        if coverage_id not in coverage_map:
            continue
        strategy = next((item for item in strategy_items if item["strategy_id"] == strategy_id and item["cov_id"] == coverage_id), None)
        if strategy is None:
            continue
        generated.append(
            _make_test_case(
                _next_test_case_id(existing_cases, generated),
                requirement["req_id"],
                coverage_map[coverage_id],
                strategy,
                risk_item,
                row,
                last_edited_by="llm",
            )
        )
    return generated


def generate_test_cases_with_report(
    ps: Dict[str, Any],
    requirement: Dict[str, Any],
    target_coverage_ids: List[str] | None,
    preserve_approved: bool,
    use_llm: bool,
    llm_client: LlmClient,
) -> Dict[str, Any]:
    req_id = requirement["req_id"]
    parsed_req = next((item for item in ps["parsed_requirements"] if item.get("req_id") == req_id and item.get("review_status") == "Approved"), None)
    if parsed_req is None:
        raise ValueError("当前需求还没有 Approved 的结构化结果。")

    risk_item = next((item for item in ps["risk_items"] if item.get("req_id") == req_id), None)
    if risk_item is None:
        raise ValueError("当前需求还没有风险评估结果。")

    approved_status = {"Approved", "Confirmed"}
    strategy_items = [
        item
        for item in ps["strategy_items"]
        if item.get("req_id") == req_id and item.get("review_status") in approved_status
    ]
    if target_coverage_ids:
        target_set = set(target_coverage_ids)
        strategy_items = [item for item in strategy_items if item.get("cov_id") in target_set]
    else:
        target_set = {item["cov_id"] for item in strategy_items}

    if not strategy_items:
        raise ValueError("当前需求还没有可用于生成用例的已批准策略项。")

    coverage_items = [
        item
        for item in ps["coverage_items"]
        if item.get("req_id") == req_id and item.get("cov_id") in target_set
    ]
    coverage_map = {item["cov_id"]: item for item in coverage_items}

    preserved: List[Dict[str, Any]] = []
    retained: List[Dict[str, Any]] = []
    replaced_count = 0
    for test_case in ps.get("test_cases", []):
        coverage_id = test_case.get("coverage_id")
        in_target = coverage_id in target_set
        approved = test_case.get("review_status") == "Approved"
        if in_target and approved and preserve_approved:
            preserved.append(test_case)
            retained.append(test_case)
        elif in_target:
            replaced_count += 1
        else:
            retained.append(test_case)

    generated: List[Dict[str, Any]] = []
    warnings: List[str] = []
    method = "rule"

    if use_llm and llm_client.enabled:
        try:
            generated = _generate_llm_cases(retained, requirement, parsed_req, coverage_items, risk_item, strategy_items, llm_client)
            if generated:
                method = "llm"
        except Exception as exc:
            warnings.append(f"LLM 生成失败，已回退到规则模板：{exc}")

    if not generated:
        method = "rule"
        for strategy_item in strategy_items:
            coverage_item = coverage_map.get(strategy_item["cov_id"])
            if coverage_item is None:
                warnings.append(f"跳过 strategy {strategy_item['strategy_id']}：找不到关联 coverage。")
                continue
            for payload in _generate_for_strategy(parsed_req, coverage_item, strategy_item, risk_item):
                generated.append(
                    _make_test_case(
                        _next_test_case_id(retained, generated),
                        req_id,
                        coverage_item,
                        strategy_item,
                        risk_item,
                        payload,
                        last_edited_by="rule",
                    )
                )

    ps["test_cases"] = retained + generated
    return {
        "test_cases": generated,
        "preserved_cases": preserved,
        "generated_count": len(generated),
        "preserved_count": len(preserved),
        "replaced_count": replaced_count,
        "method": method,
        "warnings": warnings,
        "target_coverage_ids": sorted(target_set),
    }
