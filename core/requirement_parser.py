from __future__ import annotations

import json
import re
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
- 绝对不要输出 Markdown、解释文字、注释、前后缀说明
- 绝对不要使用 ```json 代码块
- 返回内容必须是合法 JSON，所有字符串都必须用双引号包裹
- 如果某个字段没有内容，字符串字段返回 ""，列表字段返回 []
- input_fields、source_annotations、business_rules、preconditions、conditions、expected_result、error_handling、assumptions、ambiguities 必须始终存在

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


def _strip_code_fences(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    return value.strip()


def _extract_json_array(text: str) -> Any:
    candidate = _strip_code_fences(text)
    try:
        return json.loads(candidate)
    except Exception:
        match = re.search(r"\[\s*\{.*\}\s*\]", candidate, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _build_structured_payload(requirements: List[Dict[str, Any]]) -> str:
    return json.dumps(
        {
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
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _structured_batch_chat(requirements: List[Dict[str, Any]], llm_client: LlmClient, retry_hint: str = "") -> List[Dict[str, Any]]:
    prompt = STRUCTURED_BATCH_PROMPT
    if retry_hint:
        prompt = (
            f"{STRUCTURED_BATCH_PROMPT}\n\n"
            "上一次输出不是合法 JSON，请严格修正。\n"
            f"错误提示：{retry_hint}\n"
            "再次强调：只返回 JSON 数组本身，不要返回任何其他文字。"
        )
    raw_response = llm_client.chat(
        system=prompt,
        user=_build_structured_payload(requirements),
        temperature=0.0,
        max_tokens=4000,
    )
    parsed = _extract_json_array(raw_response)
    if not isinstance(parsed, list):
        snippet = raw_response[:280].replace("\n", " ")
        raise ValueError(f"LLM must return a JSON list. Raw response snippet: {snippet}")
    return [item for item in parsed if isinstance(item, dict)]


def _structured_requirements_from_llm_batch_once(requirements: List[Dict[str, Any]], llm_client: LlmClient) -> List[Dict[str, Any]]:
    parse_error: Exception | None = None
    for attempt in range(2):
        try:
            retry_hint = "" if attempt == 0 else str(parse_error)
            return _structured_batch_chat(requirements, llm_client, retry_hint=retry_hint)
        except Exception as exc:
            parse_error = exc
    raise ValueError(f"Batch structured parsing failed after retry: {parse_error}")


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

    if len(requirements) <= 2:
        try:
            result = _structured_requirements_from_llm_batch_once(requirements, llm_client)
            returned_ids = {str(item.get("requirement_id", "")).strip() for item in result}
            expected_ids = {item["requirement_id"] for item in requirements}
            if expected_ids.issubset(returned_ids):
                return result
        except Exception:
            pass

    if len(requirements) > 1:
        try:
            result = _structured_requirements_from_llm_batch_once(requirements, llm_client)
            returned_ids = {str(item.get("requirement_id", "")).strip() for item in result}
            expected_ids = {item["requirement_id"] for item in requirements}
            if expected_ids.issubset(returned_ids):
                return result
        except Exception as batch_exc:
            batch_error = batch_exc
        else:
            batch_error = ValueError("LLM batch response missing one or more requirement_id values.")
    else:
        batch_error = None

    merged_results: List[Dict[str, Any]] = []
    individual_errors: List[str] = []
    for requirement in requirements:
        try:
            rows = _structured_requirements_from_llm_batch_once([requirement], llm_client)
            if not rows:
                raise ValueError("LLM returned an empty list.")
            merged_results.append(rows[0])
        except Exception as exc:
            individual_errors.append(f"{requirement['requirement_id']}: {exc}")

    if len(merged_results) != len(requirements):
        message_parts = []
        if batch_error:
            message_parts.append(f"batch_error={batch_error}")
        if individual_errors:
            message_parts.append(f"individual_errors={' | '.join(individual_errors)}")
        raise ValueError("Structured parsing failed. " + " ; ".join(message_parts))

    return merged_results


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
