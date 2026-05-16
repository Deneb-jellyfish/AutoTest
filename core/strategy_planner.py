from __future__ import annotations

from typing import Any, Dict

from core.data_model import StrategyItem, dataclass_to_dict
from core.state_manager import find_strategy_by_cov, generate_strategy_id


TECHNIQUE_MAPPING = {
    "Input": "EP",
    "Boundary": "BVA",
    "Logic": "DT",
    "State": "ST",
    "Error": "EP",
    "UI": "EP",
    "Performance": "EP",
}


def auto_recommend_technique(coverage_item: Dict[str, Any]) -> str:
    return TECHNIQUE_MAPPING.get(coverage_item.get("category"), "EP")


def sync_strategy_for_coverage(
    ps: Dict[str, Any],
    coverage_item: Dict[str, Any],
    selected_technique: str,
    rationale: str,
    notes: str,
    review_status: str = "Confirmed",
) -> Dict[str, Any]:
    strategy = find_strategy_by_cov(ps, coverage_item["cov_id"])
    if strategy is None:
        strategy = dataclass_to_dict(
            StrategyItem(
                strategy_id=generate_strategy_id(ps),
                req_id=coverage_item["req_id"],
                cov_id=coverage_item["cov_id"],
                risk_id=coverage_item["risk_id"],
                recommended_technique=auto_recommend_technique(coverage_item),
                selected_technique=selected_technique,
                technique_rationale=rationale,
                generation_notes=notes,
                review_status=review_status,
            )
        )
        ps["strategy_items"].append(strategy)
        return strategy

    strategy["recommended_technique"] = auto_recommend_technique(coverage_item)
    strategy["selected_technique"] = selected_technique
    strategy["technique_rationale"] = rationale
    strategy["generation_notes"] = notes
    strategy["review_status"] = review_status
    return strategy
