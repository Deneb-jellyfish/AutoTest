from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, List, Optional

from core.data_model import ParsedRequirement, dataclass_to_dict, utc_now_iso
from core.llm_client import LlmClient


STRUCTURED_BATCH_PROMPT = """
你是一名资深测试分析师。
你的任务是把一组原始软件需求批量结构化，供后续测试设计使用。

重要规则：
- 你必须为输入中的每一个 requirement_id 返回且仅返回一个结构化对象
- 不允许遗漏 requirement_id
- 不要拆出不存在的需求，也不要合并不同 requirement
- source_annotations 只能引用原始需求里的原文片段
- 如果需求里信息不足，可以放到 assumptions 或 ambiguities

请只返回 JSON 数组，格式如下：
[
  {
    "requirement_id": "REQ-001",
    "summary": "一句话总结需求",
    "actor": "操作者/角色",
    "action": "用户或系统触发的动作",
    "expected_action": "系统应执行的核心行为",
    "object_under_test": "被操作对象",
    "trigger": "触发时机或入口",
    "input_fields": [
      {"name": "字段名", "type": "string|number|boolean", "description": "字段说明"}
    ],
    "business_rules": ["业务规则1"],
    "preconditions": ["前置条件1"],
    "conditions": ["条件分支1"],
    "expected_result": ["成功路径结果1"],
    "error_handling": ["异常路径结果1"],
    "assumptions": ["合理假设1"],
    "ambiguities": ["待澄清点1"],
    "source_annotations": [
      {"text": "原文片段", "category": "summary|actor|action|expected_action|trigger|input|business_rule|precondition|condition|expected_result|error_handling|ambiguity"}
    ],
    "rationale": "结构化拆解的简要依据"
  }
]
""".strip()


CATEGORY_COLORS = {
    "summary": "#FFE7BA",
    "actor": "#BFDBFE",
    "who": "#BFDBFE",
    "action": "#BBF7D0",
    "what": "#BBF7D0",
    "expected_action": "#C7F9CC",
    "trigger": "#CFFAFE",
    "input": "#FEF08A",
    "business_rule": "#FDE68A",
    "constraint": "#FDE68A",
    "precondition": "#D8B4FE",
    "condition": "#FECACA",
    "expected_result": "#E9D5FF",
    "outcome": "#E9D5FF",
    "error_handling": "#FBCFE8",
    "ambiguity": "#FED7AA",
}


def should_protect(parsed_req: Dict[str, Any]) -> bool:
    return parsed_req.get("review_status") == "Approved"


def render_annotated_text(raw_text: str, annotations: List[Dict[str, Any]]) -> str:
    html = raw_text
    sorted_annotations = sorted(
        [ann for ann in annotations if ann.get("text") and ann["text"] in raw_text],
        key=lambda item: len(str(item["text"])),
        reverse=True,
    )
    for ann in sorted_annotations:
        color = ann.get("color") or CATEGORY_COLORS.get(str(ann.get("category", "")).strip(), "#E5E7EB")
        html = html.replace(
            str(ann["text"]),
            f'<mark style="background-color:{color};padding:2px 4px;border-radius:3px;">{ann["text"]}</mark>',
            1,
        )
    return f'<div style="line-height:1.9;font-size:17px;">{html}</div>'


def build_requirement_annotation_html(raw_text: str, annotations: List[Dict[str, Any]]) -> str:
    return render_annotated_text(raw_text, annotations)


def _normalize_input_fields(items: Any) -> List[Dict[str, str]]:
    normalized = []
    for item in items or []:
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "type": str(item.get("type", "string")).strip() or "string",
                    "description": str(item.get("description", "")).strip(),
                }
            )
    return normalized


def _normalize_list(items: Any) -> List[str]:
    return [str(item).strip() for item in items or [] if str(item).strip()]


def _normalize_annotations(raw_text: str, items: Any) -> List[Dict[str, Any]]:
    annotations = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        category = str(item.get("category", "")).strip()
        if text and text in raw_text:
            annotations.append(
                {
                    "text": text,
                    "category": category,
                    "color": CATEGORY_COLORS.get(category, "#E5E7EB"),
                }
            )
    return annotations


def normalize_structured_requirement(requirement: Dict[str, Any], payload: Dict[str, Any], parsed_id: str) -> Dict[str, Any]:
    raw_text = requirement["raw_text"]
    expected_result = _normalize_list(payload.get("expected_result"))
    error_handling = _normalize_list(payload.get("error_handling"))
    business_rules = _normalize_list(payload.get("business_rules"))
    annotations = _normalize_annotations(raw_text, payload.get("source_annotations"))

    record = ParsedRequirement(
        parsed_id=parsed_id,
        requirement_id=requirement["requirement_id"],
        req_id=requirement["req_id"],
        summary=str(payload.get("summary", "")).strip(),
        actor=str(payload.get("actor", "")).strip(),
        action=str(payload.get("action", "")).strip(),
        expected_action=str(payload.get("expected_action", "")).strip(),
        object_under_test=str(payload.get("object_under_test", "")).strip(),
        trigger=str(payload.get("trigger", "")).strip(),
        input_fields=_normalize_input_fields(payload.get("input_fields")),
        business_rules=business_rules,
        preconditions=_normalize_list(payload.get("preconditions")),
        conditions=_normalize_list(payload.get("conditions")),
        expected_result=expected_result,
        error_handling=error_handling,
        assumptions=_normalize_list(payload.get("assumptions")),
        ambiguities=_normalize_list(payload.get("ambiguities")),
        source_annotations=annotations,
        rationale=str(payload.get("rationale", "")).strip(),
        review_status="Proposed",
        last_edited_by="llm",
        edit_history=[
            {
                "timestamp": utc_now_iso(),
                "editor": "llm",
                "action": "Generated",
                "reason": "Batch structuring",
            }
        ],
        who=str(payload.get("actor", "")).strip(),
        what=str(payload.get("action", "")).strip(),
        constraints=business_rules,
        expected_outcomes=expected_result + error_handling,
        system_behaviors=[],
        evidence_annotations=deepcopy(annotations),
    )
    return dataclass_to_dict(record)


def _structured_requirements_from_llm_batch(requirements: List[Dict[str, Any]], llm_client: LlmClient) -> List[Dict[str, Any]]:
    if not llm_client.enabled:
        raise RuntimeError("Structured requirement parsing requires a configured LLM.")

    payload = {
        "requirements": [
            {
                "requirement_id": item["requirement_id"],
                "title": item.get("title", ""),
                "raw_text": item["raw_text"],
                "priority": item.get("priority", "Medium"),
                "source": item.get("source", ""),
            }
            for item in requirements
        ]
    }
    result = llm_client.json_any_completion(STRUCTURED_BATCH_PROMPT, json.dumps(payload, ensure_ascii=False, indent=2))
    if not isinstance(result, list):
        raise ValueError("LLM must return a JSON list for structured requirements.")
    return [item for item in result if isinstance(item, dict)]


def parse_requirements_with_report(
    requirements: List[Dict[str, Any]],
    llm_client: LlmClient,
    parsed_id_lookup: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    llm_results = _structured_requirements_from_llm_batch(requirements, llm_client)
    by_requirement_id = {item.get("requirement_id"): item for item in llm_results}

    missing_ids = [item["requirement_id"] for item in requirements if item["requirement_id"] not in by_requirement_id]
    if missing_ids:
        raise ValueError(f"LLM response missing structured results for: {', '.join(missing_ids)}")

    parsed_records = []
    for index, requirement in enumerate(requirements, start=1):
        payload = by_requirement_id[requirement["requirement_id"]]
        parsed_id = parsed_id_lookup.get(requirement["requirement_id"], f"PR-{index:03d}") if parsed_id_lookup else f"PR-{index:03d}"
        parsed_records.append(normalize_structured_requirement(requirement, payload, parsed_id))

    return {
        "parsed_requirements": parsed_records,
        "report": {
            "input_count": len(requirements),
            "output_count": len(parsed_records),
            "missing_requirement_ids": missing_ids,
            "used_model": llm_client.config.model,
        },
    }
