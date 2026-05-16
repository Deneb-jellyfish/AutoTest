from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from core.data_model import RiskItem, dataclass_to_dict
from core.llm_client import LlmClient


RISK_SYSTEM_PROMPT = """
你是一名资深的软件测试专家，擅长风险评估。
根据下面提供的结构化需求，为其评估测试风险。

请严格按照以下 JSON 格式返回，不要返回额外文字：
{
  "risk_title": "风险标题（简短）",
  "risk_summary": "风险摘要（2-3句话）",
  "impact": 1-5的整数,
  "likelihood": 1-5的整数,
  "complexity": 1-5的整数,
  "usage_frequency": 1-5的整数,
  "rationale": "评分理由，说明各维度为什么是这个分数",
  "evidence_keywords": ["触发风险的关键词1", "关键词2"],
  "mitigation_hint": "建议测试策略，如增加边界测试、添加状态转换覆盖等"
}

评分标准：
- impact（影响度）：1=影响极小，5=核心功能失效或安全问题
- likelihood（可能性）：1=很难出错，5=逻辑复杂极易出错
- complexity（复杂度）：1=简单直接，5=多条件交叉、状态机、并发
- usage_frequency（频率）：1=极少用，5=每次操作都涉及
""".strip()


KEYWORD_RULES = {
    "high_impact": {
        "keywords": ["login", "auth", "password", "security", "登录", "认证", "密码", "安全"],
        "impact_boost": 2,
        "likelihood_boost": 1,
    },
    "high_complexity": {
        "keywords": ["lock", "state", "toggle", "filter", "锁定", "状态", "切换", "筛选"],
        "complexity_boost": 2,
        "likelihood_boost": 1,
    },
    "high_frequency": {
        "keywords": ["create", "add", "delete", "edit", "创建", "添加", "删除", "编辑"],
        "usage_frequency_boost": 2,
    },
    "validation": {
        "keywords": ["valid", "invalid", "empty", "length", "验证", "非法", "为空", "长度"],
        "likelihood_boost": 2,
        "complexity_boost": 1,
    },
}


def clamp_score(value: Any) -> int:
    try:
        value = int(value)
    except Exception:
        value = 2
    return max(1, min(5, value))


def calculate_risk_score(impact: int, likelihood: int, complexity: int, usage_frequency: int) -> int:
    return int(impact) + int(likelihood) + int(complexity) + int(usage_frequency)


def compute_risk_level(risk_score: int) -> str:
    if risk_score >= 16:
        return "High"
    if risk_score >= 10:
        return "Medium"
    return "Low"


def rule_based_score(parsed_req: Dict[str, Any]) -> Dict[str, Any]:
    text = " ".join(
        [
            parsed_req.get("who", ""),
            parsed_req.get("what", ""),
            " ".join(parsed_req.get("constraints", []) or []),
            " ".join(parsed_req.get("conditions", []) or []),
            " ".join(parsed_req.get("expected_outcomes", []) or []),
        ]
    ).lower()

    impact = 2
    likelihood = 2
    complexity = 2
    usage_frequency = 2
    triggered_keywords: List[str] = []

    for rule in KEYWORD_RULES.values():
        for keyword in rule["keywords"]:
            if keyword in text:
                impact += rule.get("impact_boost", 0)
                likelihood += rule.get("likelihood_boost", 0)
                complexity += rule.get("complexity_boost", 0)
                usage_frequency += rule.get("usage_frequency_boost", 0)
                triggered_keywords.append(keyword)
                break

    impact = clamp_score(impact)
    likelihood = clamp_score(likelihood)
    complexity = clamp_score(complexity)
    usage_frequency = clamp_score(usage_frequency)
    score = calculate_risk_score(impact, likelihood, complexity, usage_frequency)

    return {
        "risk_title": f"{parsed_req.get('what', '需求').strip()[:18]} 风险",
        "risk_summary": "基于结构化需求和关键词规则生成的初始测试风险评估。",
        "impact": impact,
        "likelihood": likelihood,
        "complexity": complexity,
        "usage_frequency": usage_frequency,
        "rationale": f"基于关键词规则评分，触发词：{', '.join(triggered_keywords) if triggered_keywords else '无'}",
        "evidence_keywords": triggered_keywords,
        "mitigation_hint": "优先覆盖高频路径、输入校验、错误提示和关键状态变化。",
        "risk_score": score,
        "risk_level": compute_risk_level(score),
    }


def normalize_risk_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    impact = clamp_score(payload.get("impact", 2))
    likelihood = clamp_score(payload.get("likelihood", 2))
    complexity = clamp_score(payload.get("complexity", 2))
    usage_frequency = clamp_score(payload.get("usage_frequency", 2))
    risk_score = calculate_risk_score(impact, likelihood, complexity, usage_frequency)
    return {
        "risk_title": str(payload.get("risk_title", "未命名风险")).strip(),
        "risk_summary": str(payload.get("risk_summary", "")).strip(),
        "impact": impact,
        "likelihood": likelihood,
        "complexity": complexity,
        "usage_frequency": usage_frequency,
        "risk_score": risk_score,
        "risk_level": compute_risk_level(risk_score),
        "rationale": str(payload.get("rationale", "")).strip(),
        "evidence_keywords": [str(item).strip() for item in payload.get("evidence_keywords", []) or [] if str(item).strip()],
        "mitigation_hint": str(payload.get("mitigation_hint", "")).strip(),
    }


def build_risk_item(
    requirement: Dict[str, Any],
    parsed_req: Dict[str, Any],
    risk_id: str,
    use_llm: bool = False,
    llm_client: Optional[LlmClient] = None,
    review_status: str = "Draft",
    last_edited_by: str = "llm",
) -> Dict[str, Any]:
    payload: Dict[str, Any]
    if use_llm and llm_client and llm_client.enabled:
        try:
            prompt_input = json.dumps(
                {
                    "requirement": requirement,
                    "parsed_requirement": parsed_req,
                },
                ensure_ascii=False,
                indent=2,
            )
            payload = normalize_risk_payload(llm_client.json_completion(RISK_SYSTEM_PROMPT, prompt_input))
        except Exception:
            payload = rule_based_score(parsed_req)
    else:
        payload = rule_based_score(parsed_req)

    risk_item = RiskItem(
        risk_id=risk_id,
        req_id=requirement["req_id"],
        parsed_id=parsed_req["parsed_id"],
        risk_title=payload["risk_title"],
        risk_summary=payload["risk_summary"],
        impact=payload["impact"],
        likelihood=payload["likelihood"],
        complexity=payload["complexity"],
        usage_frequency=payload["usage_frequency"],
        risk_score=payload["risk_score"],
        risk_level=payload["risk_level"],
        rationale=payload["rationale"],
        evidence_keywords=payload["evidence_keywords"],
        mitigation_hint=payload["mitigation_hint"],
        review_status=review_status,
        last_edited_by=last_edited_by,
    )
    return dataclass_to_dict(risk_item)
