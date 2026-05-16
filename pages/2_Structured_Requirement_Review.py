from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from core.llm_client import LlmClient, load_config
from core.requirement_parser import build_requirement_annotation_html, parse_requirements_with_report, should_protect
from core.state_manager import find_requirement, get_state, save_state
from utils.change_tracker import log_change
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


STRUCTURED_STATUS_OPTIONS = ["Proposed", "Modified", "Approved", "Rejected", "Need Clarification"]


def edit_list_block(values: List[str], key: str, label: str, placeholder: str = "") -> List[str]:
    text_value = "\n".join(values or [])
    edited = st.text_area(
        label,
        value=text_value,
        height=120,
        key=key,
        placeholder=placeholder or "每行一条",
    )
    return [line.strip() for line in edited.splitlines() if line.strip()]


def edit_input_fields(items: List[Dict[str, Any]], key: str) -> List[Dict[str, str]]:
    rows = items or [{"name": "", "type": "string", "description": ""}]
    output = []
    count_key = f"{key}_count"
    if count_key not in st.session_state:
        st.session_state[count_key] = max(1, len(rows))

    control1, control2 = st.columns([1, 5])
    with control1:
        if st.button("＋ Add", key=f"{key}_add"):
            st.session_state[count_key] += 1
    with control2:
        if st.session_state[count_key] > 1 and st.button("－ Remove Last", key=f"{key}_remove"):
            st.session_state[count_key] -= 1

    padded_rows = rows + [{"name": "", "type": "string", "description": ""}] * max(0, st.session_state[count_key] - len(rows))

    for index in range(st.session_state[count_key]):
        row = padded_rows[index]
        col1, col2, col3 = st.columns([2.2, 1.4, 3.4])
        with col1:
            name = st.text_input("name", value=str(row.get("name", "")), key=f"{key}_name_{index}", label_visibility="collapsed", placeholder="name")
        with col2:
            field_type = st.text_input("type", value=str(row.get("type", "string")), key=f"{key}_type_{index}", label_visibility="collapsed", placeholder="type")
        with col3:
            description = st.text_input("description", value=str(row.get("description", "")), key=f"{key}_desc_{index}", label_visibility="collapsed", placeholder="description")
        if not name:
            continue
        output.append(
            {
                "name": name,
                "type": field_type.strip() or "string",
                "description": description.strip(),
            }
        )
    return output


def regenerate_selected(ps: Dict[str, Any], parsed_req: Dict[str, Any], llm_client: LlmClient) -> None:
    requirement = find_requirement(ps, parsed_req["req_id"])
    result = parse_requirements_with_report([requirement], llm_client, parsed_id_lookup={requirement["requirement_id"]: parsed_req["parsed_id"]})
    new_record = result["parsed_requirements"][0]
    old_value = deepcopy(parsed_req)
    parsed_req.update(new_record)
    parsed_req["parsed_id"] = old_value["parsed_id"]
    log_change(ps, "parsed_req", parsed_req["parsed_id"], "Regenerated", "record", old_value, parsed_req, "llm", "Regenerated from structured review page")


st.set_page_config(page_title="Structured Requirement Review", layout="wide", page_icon="🧪")
apply_reference_theme()

ps = get_state()
llm_client = LlmClient(load_config())
use_llm = bool(st.session_state.get("use_llm", False))

with st.sidebar:
    render_workflow_sidebar("Structuring & Review")
    st.divider()
    st.subheader("Status Focus")
    st.caption("后续风险与覆盖页面只认 `Approved` 的结构化需求。")

render_hero(
    "AI-Assisted Requirement Structuring",
    "Structured Requirement Review",
    "Review the batch-structured output, inspect source-backed highlights, and explicitly approve what can flow downstream.",
)

if not ps["requirements"]:
    st.info("还没有原始需求。先去 Requirement Import 页面导入 requirement。")
    st.stop()

parsed_requirements = ps["parsed_requirements"]
approved_count = len([item for item in parsed_requirements if item.get("review_status") == "Approved"])
proposed_count = len([item for item in parsed_requirements if item.get("review_status") == "Proposed"])
pending_source = max(len(ps["requirements"]) - len(parsed_requirements), 0)

metric1, metric2, metric3 = st.columns(3)
with metric1:
    st.metric("Pending Structure", pending_source)
with metric2:
    st.metric("Structured Records", len(parsed_requirements))
with metric3:
    st.metric("Approved", approved_count)

if not parsed_requirements:
    st.warning("当前还没有结构化结果。请先在 Requirement Import 页面点击 `Structure Requirements`。")
    st.stop()

overview_rows = []
for item in parsed_requirements:
    overview_rows.append(
        {
            "structured_requirement_id": item["parsed_id"],
            "requirement_id": item["requirement_id"],
            "summary": item.get("summary", ""),
            "actor": item.get("actor", ""),
            "review_status": item.get("review_status", "Proposed"),
        }
    )

st.markdown("### Structured Requirements")
st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)

sorted_items = sorted(
    parsed_requirements,
    key=lambda item: (
        0 if item.get("review_status") == "Approved" else 1,
        item.get("req_id", ""),
    ),
)
labels = [
    f"{item['req_id']} - {item.get('summary') or item.get('actor') or item.get('action') or 'Structured Requirement'} [{item['review_status']}]"
    for item in sorted_items
]
label_map = {label: item for label, item in zip(labels, sorted_items)}
selected_label = st.selectbox("Select structured requirement", labels)
parsed_req = label_map[selected_label]
requirement = find_requirement(ps, parsed_req["req_id"])

control1, control2 = st.columns([1, 1.4])
with control1:
    if st.button("Regenerate Selected Requirement", use_container_width=True, type="secondary"):
        if not use_llm or not llm_client.enabled:
            st.error("结构化重生成只支持真实 LLM。")
        elif should_protect(parsed_req):
            st.session_state["confirm_regen_structured"] = True
        else:
            regenerate_selected(ps, parsed_req, llm_client)
            save_state(ps)
            st.success("已重新生成选中需求")
            st.rerun()
with control2:
    st.info("页面已从左右结构改成上下结构：先看原文高亮，再往下审核结构化字段。")

if st.session_state.get("confirm_regen_structured") and should_protect(parsed_req):
    st.warning("当前结构化记录已经 Approved。再次点击确认后会覆盖现有结果。")
    if st.button("Confirm Regenerate Approved Record", key="confirm_regen_structured_btn", type="secondary"):
        regenerate_selected(ps, parsed_req, llm_client)
        save_state(ps)
        st.session_state["confirm_regen_structured"] = False
        st.success("已覆盖 Approved 记录")
        st.rerun()

with st.expander(f"{parsed_req['parsed_id']} -> {parsed_req['requirement_id']}", expanded=True):
    st.markdown("#### Annotated Raw Text")
    st.markdown(build_requirement_annotation_html(requirement["raw_text"], parsed_req.get("source_annotations", [])), unsafe_allow_html=True)
    st.caption("Evidence source: source annotations. Color guide: blue=actor, green=action, yellow=input/business_rule, rose=condition, purple=expected_result or ambiguity.")

    annotation_rows = []
    for ann in parsed_req.get("source_annotations", []):
        annotation_rows.append(
            {
                "text": ann.get("text", ""),
                "category": ann.get("category", ""),
                "note": "",
            }
        )
    if annotation_rows:
        st.dataframe(pd.DataFrame(annotation_rows), use_container_width=True, hide_index=True)

    st.markdown("#### Structured Requirement Editor")
    summary = st.text_area("Summary", value=parsed_req.get("summary", ""), height=110, key=f"summary_{parsed_req['parsed_id']}")

    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        actor = st.text_input("Actor", value=parsed_req.get("actor", ""), key=f"actor_{parsed_req['parsed_id']}")
    with row1_col2:
        expected_action = st.text_input("Expected Action", value=parsed_req.get("expected_action", ""), key=f"expected_action_{parsed_req['parsed_id']}")

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        action = st.text_input("Action", value=parsed_req.get("action", ""), key=f"action_{parsed_req['parsed_id']}")
    with row2_col2:
        trigger = st.text_input("Trigger", value=parsed_req.get("trigger", ""), key=f"trigger_{parsed_req['parsed_id']}")

    row3_col1, row3_col2 = st.columns(2)
    with row3_col1:
        object_under_test = st.text_input("Object Under Test", value=parsed_req.get("object_under_test", ""), key=f"object_{parsed_req['parsed_id']}")
    with row3_col2:
        review_status = st.selectbox(
            "Review Status",
            STRUCTURED_STATUS_OPTIONS,
            index=STRUCTURED_STATUS_OPTIONS.index(parsed_req.get("review_status", "Proposed")) if parsed_req.get("review_status", "Proposed") in STRUCTURED_STATUS_OPTIONS else 0,
            key=f"review_status_{parsed_req['parsed_id']}",
        )

    st.markdown("##### Input Fields")
    input_fields = edit_input_fields(parsed_req.get("input_fields", []), key=f"input_fields_{parsed_req['parsed_id']}")

    business_rules = edit_list_block(
        parsed_req.get("business_rules", []),
        key=f"business_rules_{parsed_req['parsed_id']}",
        label="Business Rules",
    )
    preconditions = edit_list_block(
        parsed_req.get("preconditions", []),
        key=f"preconditions_{parsed_req['parsed_id']}",
        label="Preconditions",
    )
    conditions = edit_list_block(
        parsed_req.get("conditions", []),
        key=f"conditions_{parsed_req['parsed_id']}",
        label="Conditions",
    )
    expected_result = edit_list_block(
        parsed_req.get("expected_result", []),
        key=f"expected_result_{parsed_req['parsed_id']}",
        label="Expected Result",
    )
    error_handling = edit_list_block(
        parsed_req.get("error_handling", []),
        key=f"error_handling_{parsed_req['parsed_id']}",
        label="Error Handling",
    )
    assumptions = edit_list_block(
        parsed_req.get("assumptions", []),
        key=f"assumptions_{parsed_req['parsed_id']}",
        label="Assumptions",
    )
    ambiguities = edit_list_block(
        parsed_req.get("ambiguities", []),
        key=f"ambiguities_{parsed_req['parsed_id']}",
        label="Ambiguities",
    )
    rationale = st.text_area("Rationale", value=parsed_req.get("rationale", ""), height=120, key=f"rationale_{parsed_req['parsed_id']}")

    btn1, btn2, btn3, btn4 = st.columns(4)
    save_clicked = btn1.button("Save", type="primary")
    approve_clicked = btn2.button("Approve", type="secondary")
    reject_clicked = btn3.button("Reject", type="secondary")
    clarify_clicked = btn4.button("Need Clarification", type="secondary")

if save_clicked or approve_clicked or reject_clicked or clarify_clicked:
    old_value = deepcopy(parsed_req)
    parsed_req["summary"] = summary.strip()
    parsed_req["actor"] = actor.strip()
    parsed_req["action"] = action.strip()
    parsed_req["expected_action"] = expected_action.strip()
    parsed_req["object_under_test"] = object_under_test.strip()
    parsed_req["trigger"] = trigger.strip()
    parsed_req["input_fields"] = input_fields
    parsed_req["business_rules"] = business_rules
    parsed_req["preconditions"] = preconditions
    parsed_req["conditions"] = conditions
    parsed_req["expected_result"] = expected_result
    parsed_req["error_handling"] = error_handling
    parsed_req["assumptions"] = assumptions
    parsed_req["ambiguities"] = ambiguities
    parsed_req["rationale"] = rationale.strip()
    parsed_req["last_edited_by"] = "human"

    parsed_req["who"] = parsed_req["actor"]
    parsed_req["what"] = parsed_req["action"]
    parsed_req["constraints"] = business_rules
    parsed_req["expected_outcomes"] = expected_result + error_handling
    parsed_req["evidence_annotations"] = parsed_req.get("source_annotations", [])

    action_name = "Edited"
    if approve_clicked:
        parsed_req["review_status"] = "Approved"
        action_name = "Approved"
    elif reject_clicked:
        parsed_req["review_status"] = "Rejected"
        action_name = "Rejected"
    elif clarify_clicked:
        parsed_req["review_status"] = "Need Clarification"
        action_name = "Need Clarification"
    else:
        parsed_req["review_status"] = review_status
        if review_status == "Modified":
            action_name = "Modified"

    parsed_req.setdefault("edit_history", []).append(
        {
            "timestamp": pd.Timestamp.now().isoformat(),
            "editor": "human",
            "action": action_name,
            "reason": "Manual structured review",
        }
    )
    log_change(ps, "parsed_req", parsed_req["parsed_id"], action_name, "record", old_value, parsed_req, "human", "Manual structured review")
    save_state(ps)
    st.success(f"{parsed_req['parsed_id']} 已更新为 {parsed_req['review_status']}")
    st.rerun()

st.markdown("### 审查历史")
history = [item for item in ps["audit_log"] if item.get("object_id") == parsed_req["parsed_id"]]
if history:
    for item in reversed(history):
        st.write(
            f"`{item['timestamp']}` | `{item['changed_by']}` | `{item['action']}` | "
            f"`{item['changed_field']}` | {item.get('reason') or '无'}"
        )
else:
    st.caption("当前结构化记录还没有审查历史。")
