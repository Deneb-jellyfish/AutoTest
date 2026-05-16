from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from core.data_model import COVERAGE_CATEGORIES, CoverageItem, dataclass_to_dict
from core.llm_client import LlmClient


COVERAGE_SYSTEM_PROMPT = """
你是一名专业的软件测试工程师，熟悉 ISO 29119-4 测试技术。
根据提供的结构化需求和风险信息，识别所有需要测试的覆盖项。

请严格按照以下 JSON 格式返回，不要返回额外文字：
{
  "coverage_items": [
    {
      "category": "Input|Boundary|Logic|State|Error|UI|Performance",
      "title": "覆盖项标题",
      "description": "描述这个覆盖项在测什么",
      "test_focus": "核心验证点",
      "input_partitions": ["等价类1", "等价类2"],
      "boundary_values": ["边界值1", "边界值2"],
      "suggested_technique": "EP|BVA|DT|ST",
      "technique_rationale": "为什么推荐这个技术"
    }
  ]
}

生成规则：
- Input 类别：必须为每个输入字段生成等价类（有效/无效/边界）
- Boundary 类别：数值或长度限制必须生成边界值（刚好满足/刚好超出）
- Logic 类别：多条件组合要考虑决策表
- State 类别：有状态切换的要生成状态转换测试
- Error 类别：每种错误路径要单独一个覆盖项
- 不要遗漏 ambiguities 里提到的歧义情况，可以生成一条 "Needs Clarification" 的覆盖项

技术映射参考：
- EP（等价类划分）-> Input/Error
- BVA（边界值分析）-> Boundary
- DT（决策表）-> Logic（多条件）
- ST（状态转换）-> State
""".strip()


def _clean_list(items: Any) -> List[str]:
    return [str(item).strip() for item in items or [] if str(item).strip()]


def _parse_boundary_values(constraints: List[str]) -> List[str]:
    boundary_values: List[str] = []
    for text in constraints:
        for low, high in re.findall(r"(\d+)\D+(\d+)", text):
            boundary_values.extend([str(max(0, int(low) - 1)), low, high, str(int(high) + 1)])
    return list(dict.fromkeys(boundary_values))


def _fallback_coverage_payload(parsed_req: Dict[str, Any], risk_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    coverage_items: List[Dict[str, Any]] = []

    for field in parsed_req.get("input_fields", []) or []:
        name = field.get("name", "field")
        coverage_items.append(
            {
                "category": "Input",
                "title": f"{name} 等价类划分",
                "description": f"验证字段 {name} 的有效输入、无效输入和空输入。",
                "test_focus": f"确认 {name} 的输入校验规则符合需求。",
                "input_partitions": ["valid", "empty", "invalid"],
                "boundary_values": [],
                "suggested_technique": "EP",
                "technique_rationale": "输入字段最适合先做等价类划分。",
            }
        )

    boundary_values = _parse_boundary_values(parsed_req.get("constraints", []) or [])
    if boundary_values:
        coverage_items.append(
            {
                "category": "Boundary",
                "title": "约束边界值覆盖",
                "description": "针对长度或数值限制生成边界值覆盖项。",
                "test_focus": "验证刚好满足和刚好超出时系统行为是否正确。",
                "input_partitions": ["below_min", "at_min", "at_max", "above_max"],
                "boundary_values": boundary_values,
                "suggested_technique": "BVA",
                "technique_rationale": "需求中存在边界限制，适合做边界值分析。",
            }
        )

    if len(parsed_req.get("conditions", []) or []) >= 2:
        coverage_items.append(
            {
                "category": "Logic",
                "title": "条件组合逻辑覆盖",
                "description": "验证多个触发条件组合下的系统决策路径。",
                "test_focus": "确认条件交叉时不会遗漏分支。",
                "input_partitions": _clean_list(parsed_req.get("conditions")),
                "boundary_values": [],
                "suggested_technique": "DT",
                "technique_rationale": "多条件组合场景适合决策表。",
            }
        )

    state_text = " ".join(
        [parsed_req.get("what", "")] + _clean_list(parsed_req.get("system_behaviors")) + _clean_list(parsed_req.get("expected_outcomes"))
    ).lower()
    if any(keyword in state_text for keyword in ["toggle", "switch", "state", "切换", "状态", "锁定", "完成"]):
        coverage_items.append(
            {
                "category": "State",
                "title": "状态切换覆盖",
                "description": "验证状态从一种状态切换到另一种状态时的正确性。",
                "test_focus": "确认状态迁移和列表显示保持一致。",
                "input_partitions": ["before_transition", "after_transition"],
                "boundary_values": [],
                "suggested_technique": "ST",
                "technique_rationale": "存在明显状态变化，适合状态转换测试。",
            }
        )

    error_paths = []
    for condition in parsed_req.get("conditions", []) or []:
        if any(keyword in condition for keyword in ["为空", "超过", "失败", "错误", "invalid", "empty", "incorrect"]):
            error_paths.append(condition)
    if error_paths or any("错误" in item or "error" in item.lower() for item in parsed_req.get("expected_outcomes", []) or []):
        coverage_items.append(
            {
                "category": "Error",
                "title": "错误处理路径覆盖",
                "description": "覆盖异常输入、非法条件或失败路径的系统反馈。",
                "test_focus": "确认错误提示准确、阻止非法提交。",
                "input_partitions": ["invalid_input", "rejected_action"],
                "boundary_values": [],
                "suggested_technique": "EP",
                "technique_rationale": "错误路径通常可按非法等价类组织。",
            }
        )

    if any("显示" in item or "提示" in item for item in parsed_req.get("expected_outcomes", []) or []):
        coverage_items.append(
            {
                "category": "UI",
                "title": "界面反馈覆盖",
                "description": "检查错误提示、成功提示和界面展示是否正确。",
                "test_focus": "验证用户看到的反馈信息与状态一致。",
                "input_partitions": ["success_feedback", "error_feedback"],
                "boundary_values": [],
                "suggested_technique": "EP",
                "technique_rationale": "UI 反馈可按展示场景做覆盖。",
            }
        )

    for ambiguity in parsed_req.get("ambiguities", []) or []:
        coverage_items.append(
            {
                "category": "Logic",
                "title": f"Needs Clarification - {ambiguity[:24]}",
                "description": "为需求歧义保留覆盖占位，提醒后续澄清。",
                "test_focus": ambiguity,
                "input_partitions": ["clarify_with_pm"],
                "boundary_values": [],
                "suggested_technique": "DT",
                "technique_rationale": "歧义会影响分支判断，需要先明确规则。",
            }
        )

    if not coverage_items:
        coverage_items.append(
            {
                "category": "Input",
                "title": "基础输入覆盖",
                "description": "规则引擎未识别到细粒度覆盖项时的默认覆盖。",
                "test_focus": "至少覆盖主流程和基础错误路径。",
                "input_partitions": ["valid", "invalid"],
                "boundary_values": [],
                "suggested_technique": "EP",
                "technique_rationale": "默认回退为等价类划分。",
            }
        )

    return coverage_items


def normalize_coverage_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    normalized = []
    for item in payload.get("coverage_items", []) or []:
        category = str(item.get("category", "Input")).strip()
        if category not in COVERAGE_CATEGORIES:
            category = "Input"
        normalized.append(
            {
                "category": category,
                "title": str(item.get("title", "")).strip() or "未命名覆盖项",
                "description": str(item.get("description", "")).strip(),
                "test_focus": str(item.get("test_focus", "")).strip(),
                "input_partitions": _clean_list(item.get("input_partitions")),
                "boundary_values": _clean_list(item.get("boundary_values")),
                "suggested_technique": str(item.get("suggested_technique", "EP")).strip() or "EP",
                "technique_rationale": str(item.get("technique_rationale", "")).strip(),
            }
        )
    return normalized


def build_coverage_items(
    requirement: Dict[str, Any],
    parsed_req: Dict[str, Any],
    risk_item: Dict[str, Any],
    starting_index: int,
    use_llm: bool = False,
    llm_client: Optional[LlmClient] = None,
    review_status: str = "Draft",
    last_edited_by: str = "llm",
) -> List[Dict[str, Any]]:
    raw_items: List[Dict[str, Any]]
    if use_llm and llm_client and llm_client.enabled:
        try:
            prompt_input = json.dumps(
                {
                    "requirement": requirement,
                    "parsed_requirement": parsed_req,
                    "risk_item": risk_item,
                },
                ensure_ascii=False,
                indent=2,
            )
            raw_items = normalize_coverage_payload(llm_client.json_completion(COVERAGE_SYSTEM_PROMPT, prompt_input))
        except Exception:
            raw_items = _fallback_coverage_payload(parsed_req, risk_item)
    else:
        raw_items = _fallback_coverage_payload(parsed_req, risk_item)

    output = []
    for offset, item in enumerate(raw_items, start=starting_index):
        coverage = CoverageItem(
            cov_id=f"COV-{offset:03d}",
            req_id=requirement["req_id"],
            parsed_id=parsed_req["parsed_id"],
            risk_id=risk_item["risk_id"],
            category=item["category"],
            title=item["title"],
            description=item["description"],
            test_focus=item["test_focus"],
            input_partitions=item["input_partitions"],
            boundary_values=item["boundary_values"],
            suggested_technique=item["suggested_technique"],
            risk_level=risk_item["risk_level"],
            review_status=review_status,
            last_edited_by=last_edited_by,
        )
        output.append(dataclass_to_dict(coverage))
    return output


def check_coverage_gaps(parsed_req: Dict[str, Any], coverage_items: List[Dict[str, Any]]) -> List[str]:
    gaps = []
    categories_present = {item.get("category") for item in coverage_items}

    if parsed_req.get("input_fields") and "Input" not in categories_present:
        gaps.append("⚠️ 检测到输入字段，但没有 Input 类型的覆盖项")

    constraints_text = " ".join(parsed_req.get("constraints", []) or [])
    if any(keyword in constraints_text for keyword in ["长度", "字符", "length", "chars"]) and "Boundary" not in categories_present:
        gaps.append("⚠️ 需求有长度约束，但没有 Boundary 类型的覆盖项")

    if len(parsed_req.get("conditions", []) or []) >= 2 and "Logic" not in categories_present:
        gaps.append("⚠️ 有多个触发条件，建议添加 Logic（决策表）类型覆盖项")

    what_text = parsed_req.get("what", "")
    if any(keyword in what_text for keyword in ["toggle", "switch", "state", "切换", "状态"]) and "State" not in categories_present:
        gaps.append("⚠️ 操作涉及状态切换，建议添加 State 类型覆盖项")

    if parsed_req.get("ambiguities") and not any(
        "clarif" in item.get("title", "").lower() or "歧义" in item.get("title", "")
        for item in coverage_items
    ):
        gaps.append(f"ℹ️ 需求存在 {len(parsed_req['ambiguities'])} 处歧义，建议为其创建覆盖项或在文档中说明")

    return gaps
