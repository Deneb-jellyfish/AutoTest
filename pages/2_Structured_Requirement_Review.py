from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from core.llm_client import LlmClient, load_config
from core.requirement_parser import build_requirement_annotation_html, parse_requirements_with_report, should_protect
from core.state_manager import find_requirement, generate_parsed_id, get_state, save_state
from utils.change_tracker import log_change
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


STRUCTURED_STATUS_OPTIONS = ["Proposed", "Modified", "Approved", "Rejected", "Need Clarification"]
STRUCTURED_STATUS_RANK = {
    "Proposed": 0,
    "Modified": 1,
    "Need Clarification": 2,
    "Approved": 3,
    "Rejected": 4,
}


def stringify_value(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return ""
        if all(isinstance(item, dict) for item in value):
            parts = []
            for item in value:
                compact = ", ".join(
                    f"{field}={item.get(field, '')}"
                    for field in item.keys()
                    if str(item.get(field, "")).strip()
                )
                if compact:
                    parts.append(compact)
            return " | ".join(parts)
        return " | ".join(str(item).strip() for item in value if str(item).strip())
    if value is None:
        return ""
    return str(value)


def build_structured_overview_rows(parsed_requirements: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for item in parsed_requirements:
        rows.append(
            {
                "structured_requirement_id": item.get("parsed_id", ""),
                "requirement_id": item.get("requirement_id", ""),
                "summary": item.get("summary", ""),
                "actor": item.get("actor", ""),
                "action": item.get("action", ""),
                "expected_action": item.get("expected_action", ""),
                "object_under_test": item.get("object_under_test", ""),
                "trigger": item.get("trigger", ""),
                "input_fields": stringify_value(item.get("input_fields", [])),
                "business_rules": stringify_value(item.get("business_rules", [])),
                "preconditions": stringify_value(item.get("preconditions", [])),
                "conditions": stringify_value(item.get("conditions", [])),
                "expected_result": stringify_value(item.get("expected_result", [])),
                "error_handling": stringify_value(item.get("error_handling", [])),
                "assumptions": stringify_value(item.get("assumptions", [])),
                "ambiguities": stringify_value(item.get("ambiguities", [])),
                "source_annotations": stringify_value(item.get("source_annotations", [])),
                "rationale": item.get("rationale", ""),
                "review_status": item.get("review_status", "Proposed"),
                "last_edited_by": item.get("last_edited_by", ""),
            }
        )
    return rows


def build_pending_requirement_rows(requirements: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for item in requirements:
        rows.append(
            {
                "requirement_id": item.get("requirement_id", item.get("req_id", "")),
                "title": item.get("title", ""),
                "priority": item.get("priority", ""),
                "review_status": item.get("review_status", "Imported"),
                "source": item.get("source", ""),
                "raw_text": item.get("raw_text", ""),
            }
        )
    return rows


def get_pending_requirements(ps: Dict[str, Any]) -> List[Dict[str, Any]]:
    structured_ids = {item.get("requirement_id", item.get("req_id")) for item in ps["parsed_requirements"]}
    return [
        item
        for item in ps["requirements"]
        if item.get("requirement_id", item.get("req_id")) not in structured_ids
    ]


def sync_structured_results(ps: Dict[str, Any], parsed_records: List[Dict[str, Any]], reason: str) -> tuple[int, int]:
    updated = 0
    skipped = 0
    existing_map = {item["requirement_id"]: item for item in ps["parsed_requirements"]}

    for record in parsed_records:
        existing = existing_map.get(record["requirement_id"])
        if existing and should_protect(existing):
            skipped += 1
            continue
        if existing:
            old_value = deepcopy(existing)
            existing.update(record)
            existing["parsed_id"] = old_value["parsed_id"]
            log_change(ps, "parsed_req", existing["parsed_id"], "Regenerated", "record", old_value, existing, "llm", reason)
        else:
            record["parsed_id"] = generate_parsed_id(ps)
            ps["parsed_requirements"].append(record)
            log_change(ps, "parsed_req", record["parsed_id"], "Created", "record", None, record, "llm", reason)
        updated += 1

    parsed_requirement_ids = {item["requirement_id"] for item in parsed_records}
    for requirement in ps["requirements"]:
        if requirement["requirement_id"] in parsed_requirement_ids:
            requirement["review_status"] = "Structured"
    return updated, skipped


def build_structured_label(parsed_req: Dict[str, Any]) -> str:
    summary = parsed_req.get("summary") or parsed_req.get("actor") or parsed_req.get("action") or "Structured Requirement"
    return f"{parsed_req['req_id']} - {summary} [{parsed_req.get('review_status', 'Proposed')}]"


def edit_list_block(values: List[str], key: str, label: str, placeholder: str = "") -> List[str]:
    text_value = "\n".join(values or [])
    edited = st.text_area(
        label,
        value=text_value,
        height=120,
        key=key,
        placeholder=placeholder or "One item per line",
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
        if st.button("+ Add", key=f"{key}_add"):
            st.session_state[count_key] += 1
    with control2:
        if st.session_state[count_key] > 1 and st.button("- Remove Last", key=f"{key}_remove"):
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
    if requirement is None:
        raise ValueError(f"Cannot find source requirement for {parsed_req['req_id']}")
    result = parse_requirements_with_report([requirement], llm_client, parsed_id_lookup={requirement["requirement_id"]: parsed_req["parsed_id"]})
    new_record = result["parsed_requirements"][0]
    old_value = deepcopy(parsed_req)
    parsed_req.update(new_record)
    parsed_req["parsed_id"] = old_value["parsed_id"]
    log_change(ps, "parsed_req", parsed_req["parsed_id"], "Regenerated", "record", old_value, parsed_req, "llm", "Regenerated from structured review page")


def structure_pending_requirements(ps: Dict[str, Any], llm_client: LlmClient) -> None:
    pending_requirements = get_pending_requirements(ps)
    if not pending_requirements:
        st.info("All requirements already have structured results.")
        return

    parsed_id_lookup = {
        item["requirement_id"]: item["parsed_id"]
        for item in ps["parsed_requirements"]
    }
    result = parse_requirements_with_report(pending_requirements, llm_client, parsed_id_lookup=parsed_id_lookup)
    updated, skipped = sync_structured_results(ps, result["parsed_requirements"], "Batch structure from structured review page")
    log_change(
        ps,
        "parsed_req",
        "batch_pending",
        "Regenerated",
        "record",
        None,
        result["report"],
        "llm",
        f"Structured {updated} pending requirements; skipped {skipped} protected records",
    )
    save_state(ps)
    st.success(f"Structured {updated} pending requirements, skipped {skipped} protected records.")
    st.rerun()


def render_structured_requirement_card(ps: Dict[str, Any], parsed_req: Dict[str, Any], llm_client: LlmClient, use_llm: bool, expanded: bool = False) -> None:
    requirement = find_requirement(ps, parsed_req["req_id"])
    label = build_structured_label(parsed_req)
    expander_title = f"{parsed_req['parsed_id']} -> {label}"
    card_key = f"{parsed_req['parsed_id']}_{parsed_req['requirement_id']}"

    with st.expander(expander_title, expanded=expanded):
        top_left, top_right = st.columns([1, 1.2])
        with top_left:
            st.caption(f"Source requirement: `{parsed_req['requirement_id']}`")
        with top_right:
            if st.button("Regenerate This Requirement", key=f"regen_{card_key}", use_container_width=True):
                if not use_llm or not llm_client.enabled:
                    st.error("Requirement regeneration needs a configured LLM.")
                elif should_protect(parsed_req):
                    st.session_state["confirm_regen_structured"] = card_key
                else:
                    regenerate_selected(ps, parsed_req, llm_client)
                    save_state(ps)
                    st.success(f"{parsed_req['parsed_id']} regenerated.")
                    st.rerun()

        if st.session_state.get("confirm_regen_structured") == card_key and should_protect(parsed_req):
            st.warning("This record is Approved. Regenerating it will overwrite the approved structured result.")
            confirm_col1, confirm_col2 = st.columns([1, 4])
            with confirm_col1:
                if st.button("Confirm", key=f"confirm_regen_structured_btn_{card_key}", type="secondary"):
                    regenerate_selected(ps, parsed_req, llm_client)
                    save_state(ps)
                    st.session_state["confirm_regen_structured"] = None
                    st.success(f"{parsed_req['parsed_id']} regenerated.")
                    st.rerun()
            with confirm_col2:
                if st.button("Cancel", key=f"cancel_regen_structured_btn_{card_key}"):
                    st.session_state["confirm_regen_structured"] = None
                    st.rerun()

        if requirement is not None:
            st.markdown("#### Annotated Raw Text")
            st.markdown(build_requirement_annotation_html(requirement["raw_text"], parsed_req.get("source_annotations", [])), unsafe_allow_html=True)
            st.caption("Evidence source: source annotations. Color guide: blue=actor, green=action, yellow=input or business rule, rose=condition, purple=expected result or ambiguity.")

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
        summary = st.text_area("Summary", value=parsed_req.get("summary", ""), height=110, key=f"summary_{card_key}")

        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            actor = st.text_input("Actor", value=parsed_req.get("actor", ""), key=f"actor_{card_key}")
        with row1_col2:
            expected_action = st.text_input("Expected Action", value=parsed_req.get("expected_action", ""), key=f"expected_action_{card_key}")

        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            action = st.text_input("Action", value=parsed_req.get("action", ""), key=f"action_{card_key}")
        with row2_col2:
            trigger = st.text_input("Trigger", value=parsed_req.get("trigger", ""), key=f"trigger_{card_key}")

        row3_col1, row3_col2 = st.columns(2)
        with row3_col1:
            object_under_test = st.text_input("Object Under Test", value=parsed_req.get("object_under_test", ""), key=f"object_{card_key}")
        with row3_col2:
            review_status = st.selectbox(
                "Review Status",
                STRUCTURED_STATUS_OPTIONS,
                index=STRUCTURED_STATUS_OPTIONS.index(parsed_req.get("review_status", "Proposed")) if parsed_req.get("review_status", "Proposed") in STRUCTURED_STATUS_OPTIONS else 0,
                key=f"review_status_{card_key}",
            )

        st.markdown("##### Input Fields")
        input_fields = edit_input_fields(parsed_req.get("input_fields", []), key=f"input_fields_{card_key}")

        business_rules = edit_list_block(parsed_req.get("business_rules", []), key=f"business_rules_{card_key}", label="Business Rules")
        preconditions = edit_list_block(parsed_req.get("preconditions", []), key=f"preconditions_{card_key}", label="Preconditions")
        conditions = edit_list_block(parsed_req.get("conditions", []), key=f"conditions_{card_key}", label="Conditions")
        expected_result = edit_list_block(parsed_req.get("expected_result", []), key=f"expected_result_{card_key}", label="Expected Result")
        error_handling = edit_list_block(parsed_req.get("error_handling", []), key=f"error_handling_{card_key}", label="Error Handling")
        assumptions = edit_list_block(parsed_req.get("assumptions", []), key=f"assumptions_{card_key}", label="Assumptions")
        ambiguities = edit_list_block(parsed_req.get("ambiguities", []), key=f"ambiguities_{card_key}", label="Ambiguities")
        rationale = st.text_area("Rationale", value=parsed_req.get("rationale", ""), height=120, key=f"rationale_{card_key}")

        btn1, btn2, btn3, btn4 = st.columns(4)
        save_clicked = btn1.button("Save", key=f"save_{card_key}", type="primary")
        approve_clicked = btn2.button("Approve", key=f"approve_{card_key}", type="secondary")
        reject_clicked = btn3.button("Reject", key=f"reject_{card_key}", type="secondary")
        clarify_clicked = btn4.button("Need Clarification", key=f"clarify_{card_key}", type="secondary")

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
            st.success(f"{parsed_req['parsed_id']} updated to {parsed_req['review_status']}.")
            st.rerun()

        st.markdown("#### Review History")
        history = [item for item in ps["audit_log"] if item.get("object_id") == parsed_req["parsed_id"]]
        if history:
            for item in reversed(history):
                st.write(
                    f"`{item['timestamp']}` | `{item['changed_by']}` | `{item['action']}` | "
                    f"`{item['changed_field']}` | {item.get('reason') or ''}"
                )
        else:
            st.caption("No review history yet for this structured record.")


st.set_page_config(page_title="Structured Requirement Review", layout="wide", page_icon=":memo:")
apply_reference_theme()

ps = get_state()
llm_client = LlmClient(load_config())
use_llm = bool(st.session_state.get("use_llm", False))

with st.sidebar:
    render_workflow_sidebar("Structuring & Review")
    st.divider()
    st.subheader("Status Focus")
    st.caption("Only `Approved` structured requirements will flow into downstream risk and coverage pages.")

render_hero(
    "AI-Assisted Requirement Structuring",
    "Structured Requirement Review",
    "Review the batch-structured output, inspect source-backed highlights, and explicitly approve what can flow downstream.",
)

if not ps["requirements"]:
    st.info("No raw requirements yet. Import requirements first from the Requirement Import page.")
    st.stop()

parsed_requirements = ps["parsed_requirements"]
approved_count = len([item for item in parsed_requirements if item.get("review_status") == "Approved"])
pending_requirements = get_pending_requirements(ps)
pending_source = len(pending_requirements)

metric1, metric2, metric3 = st.columns(3)
with metric1:
    st.metric("Pending Structure", pending_source)
with metric2:
    st.metric("Structured Records", len(parsed_requirements))
with metric3:
    st.metric("Approved", approved_count)

if pending_requirements:
    st.markdown("### Pending Requirements")
    st.dataframe(pd.DataFrame(build_pending_requirement_rows(pending_requirements)), use_container_width=True, hide_index=True)

    pending_action_col, pending_hint_col = st.columns([1, 1.5])
    with pending_action_col:
        if st.button("Structure Pending Requirements", type="primary", use_container_width=True):
            if not use_llm or not llm_client.enabled:
                st.error("Structuring pending requirements needs a configured LLM.")
            else:
                structure_pending_requirements(ps, llm_client)
    with pending_hint_col:
        st.info("Newly added requirements stay here until they are structured. Click the button to generate structured results for all pending items.")

if not parsed_requirements:
    st.warning("No structured results yet. Use the pending-structure action above, or structure requirements from the import page.")
    st.stop()

st.markdown("### Structured Requirements")
st.dataframe(pd.DataFrame(build_structured_overview_rows(parsed_requirements)), use_container_width=True, hide_index=True)

st.markdown("### Structured Requirement Details")
st.caption("All structured results are shown below. You can review, edit, approve, or regenerate each record in place.")

sorted_items = sorted(
    parsed_requirements,
    key=lambda item: (
        STRUCTURED_STATUS_RANK.get(item.get("review_status", "Proposed"), 99),
        item.get("req_id", ""),
    ),
)

for index, parsed_req in enumerate(sorted_items):
    render_structured_requirement_card(
        ps,
        parsed_req,
        llm_client,
        use_llm,
        expanded=index == 0,
    )
