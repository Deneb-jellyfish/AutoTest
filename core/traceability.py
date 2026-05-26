from __future__ import annotations

from typing import Any, Dict, List


def build_traceability_matrix(project_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    requirements = {item.get("req_id") or item.get("requirement_id"): item for item in project_state.get("requirements", [])}
    parsed_by_id = {item.get("parsed_id"): item for item in project_state.get("parsed_requirements", [])}
    risks_by_id = {item.get("risk_id"): item for item in project_state.get("risk_items", [])}
    strategies_by_cov: Dict[str, List[Dict[str, Any]]] = {}
    test_cases_by_cov: Dict[str, List[Dict[str, Any]]] = {}

    for item in project_state.get("strategy_items", []):
        strategies_by_cov.setdefault(item.get("cov_id", ""), []).append(item)
    for item in project_state.get("test_cases", []):
        test_cases_by_cov.setdefault(item.get("coverage_id", ""), []).append(item)

    matrix: List[Dict[str, Any]] = []
    for coverage_item in project_state.get("coverage_items", []):
        coverage_id = coverage_item.get("cov_id", "")
        requirement_id = coverage_item.get("req_id", "")
        parsed_id = coverage_item.get("parsed_id", "")
        risk_id = coverage_item.get("risk_id", "")

        linked_strategies = strategies_by_cov.get(coverage_id, [])
        if not linked_strategies:
            matrix.append(
                {
                    "requirement_id": requirement_id,
                    "structured_requirement_id": parsed_id,
                    "risk_id": risk_id,
                    "coverage_id": coverage_id,
                    "strategy_id": "",
                    "test_case_id": "",
                    "suite_ids": coverage_item.get("suite_ids", []),
                    "coverage_title": coverage_item.get("title", ""),
                    "strategy_technique": "",
                    "test_case_title": "",
                    "gap_note": "Coverage item has no mapped strategy.",
                }
            )
            continue

        for strategy_item in linked_strategies:
            linked_cases = [
                item
                for item in test_cases_by_cov.get(coverage_id, [])
                if item.get("strategy_id") == strategy_item.get("strategy_id")
            ]
            if not linked_cases:
                matrix.append(
                    {
                        "requirement_id": requirement_id,
                        "structured_requirement_id": parsed_id,
                        "risk_id": risk_id,
                        "coverage_id": coverage_id,
                        "strategy_id": strategy_item.get("strategy_id", ""),
                        "test_case_id": "",
                        "suite_ids": coverage_item.get("suite_ids", []),
                        "coverage_title": coverage_item.get("title", ""),
                        "strategy_technique": strategy_item.get("selected_technique", ""),
                        "test_case_title": "",
                        "gap_note": "Strategy item has no generated test case.",
                    }
                )
                continue

            for test_case in linked_cases:
                matrix.append(
                    {
                        "requirement_id": requirement_id,
                        "structured_requirement_id": parsed_id,
                        "risk_id": risk_id,
                        "coverage_id": coverage_id,
                        "strategy_id": strategy_item.get("strategy_id", ""),
                        "test_case_id": test_case.get("test_case_id", ""),
                        "suite_ids": test_case.get("suite_ids", coverage_item.get("suite_ids", [])),
                        "coverage_title": coverage_item.get("title", ""),
                        "strategy_technique": strategy_item.get("selected_technique", ""),
                        "test_case_title": test_case.get("title", ""),
                        "gap_note": "",
                    }
                )

    uncovered_requirements = set(requirements) - {row.get("requirement_id", "") for row in matrix}
    for requirement_id in sorted(item for item in uncovered_requirements if item):
        requirement = requirements[requirement_id]
        matrix.append(
            {
                "requirement_id": requirement_id,
                "structured_requirement_id": "",
                "risk_id": "",
                "coverage_id": "",
                "strategy_id": "",
                "test_case_id": "",
                "suite_ids": [],
                "coverage_title": "",
                "strategy_technique": "",
                "test_case_title": "",
                "gap_note": "Requirement has no coverage item.",
            }
        )

    return matrix
