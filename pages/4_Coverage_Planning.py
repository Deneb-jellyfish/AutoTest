from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from core.coverage_builder import build_coverage_items, check_coverage_gaps
from core.data_model import COVERAGE_CATEGORIES, TECHNIQUES, CoverageItem, dataclass_to_dict
from core.llm_client import LlmClient, load_config
from core.state_manager import (
    find_coverage,
    find_requirement,
    find_risk_by_req_id,
    find_strategy_by_cov,
    generate_coverage_id,
    get_state,
    save_state,
)
from core.strategy_planner import auto_recommend_technique, sync_strategy_for_coverage
from utils.change_tracker import log_change
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


CATEGORY_BADGE_COLORS = {
    "Input": "#DBEAFE",
    "Boundary": "#D1FAE5",
    "Logic": "#FEF3C7",
    "State": "#EDE9FE",
    "Error": "#FEE2E2",
    "UI": "#E0F2FE",
    "Performance": "#FFF7ED",
}

TECHNIQUE_COLORS = {
    "EP": "#BFDBFE",
    "BVA": "#BBF7D0",
    "DT": "#FDE68A",
    "ST": "#DDD6FE",
}


def edit_string_list(items: List[str], key: str, label: str) -> List[str]:
    frame = pd.DataFrame({"value": items or [""]})
    edited = st.data_editor(frame, num_rows="dynamic", use_container_width=True, key=key)
    st.caption(label)
    return [str(value).strip() for value in edited["value"].tolist() if str(value).strip()]


def next_coverage_number(ps: Dict[str, Any]) -> int:
    max_num = 0
    for item in ps["coverage_items"]:
        raw = str(item.get("cov_id", ""))
        if raw.startswith("COV-"):
            suffix = raw.split("-", 1)[1]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return max_num + 1


def regenerate_coverage_for_requirement(
    ps: Dict[str, Any],
    requirement: Dict[str, Any],
    parsed_req: Dict[str, Any],
    risk_item: Dict[str, Any],
    use_llm: bool,
    llm_client: LlmClient,
) -> int:
    existing_draft_items = [item for item in ps["coverage_items"] if item["req_id"] == requirement["req_id"] and item.get("review_status") != "Confirmed"]
    for item in existing_draft_items:
        log_change(ps, "coverage_item", item["cov_id"], "Regenerated", "record", item, None, "llm", "Removed before regeneration")
    draft_ids = {item["cov_id"] for item in existing_draft_items}
    ps["coverage_items"] = [item for item in ps["coverage_items"] if item["cov_id"] not in draft_ids]
    ps["strategy_items"] = [item for item in ps["strategy_items"] if item["cov_id"] not in draft_ids]

    generated = build_coverage_items(
        requirement,
        parsed_req,
        risk_item,
        starting_index=next_coverage_number(ps),
        use_llm=use_llm,
        llm_client=llm_client,
        review_status="Draft",
        last_edited_by="llm",
    )
    for item in generated:
        ps["coverage_items"].append(item)
        log_change(ps, "coverage_item", item["cov_id"], "Created", "record", None, item, "llm", "Coverage generation")
    return len(generated)


apply_reference_theme()

ps = get_state()
use_llm = bool(st.session_state.get("use_llm", False))
llm_client = LlmClient(load_config())

with st.sidebar:
    render_workflow_sidebar("Coverage & Strategy")

render_hero(
    "Coverage Planning",
    "Coverage & Strategy",
    "Turn approved structured requirements and scored risks into editable coverage items, then map each one to a practical test technique.",
)

eligible_requirements = []
for parsed_req in ps["parsed_requirements"]:
    if parsed_req.get("review_status") != "Approved":
        continue
    risk_item = find_risk_by_req_id(ps, parsed_req["req_id"])
    if risk_item is None:
        continue
    requirement = find_requirement(ps, parsed_req["req_id"])
    eligible_requirements.append((risk_item["risk_score"], requirement, parsed_req, risk_item))

eligible_requirements.sort(key=lambda item: item[0], reverse=True)

if not eligible_requirements:
    st.info("还没有可规划覆盖项的需求。请先完成结构化 `Approved` 和风险评估。")
    st.stop()

labels = [
    f"{req['req_id']} - {req['title']} [{risk['risk_level']} / {risk['risk_score']}分]"
    for _, req, _, risk in eligible_requirements
]
label_map = {
    f"{req['req_id']} - {req['title']} [{risk['risk_level']} / {risk['risk_score']}分]": (req, parsed, risk)
    for _, req, parsed, risk in eligible_requirements
}

selected_label = st.selectbox("需求选择器（按风险分降序排列）", labels)
requirement, parsed_req, risk_item = label_map[selected_label]

coverage_items_for_req = [item for item in ps["coverage_items"] if item["req_id"] == requirement["req_id"]]
confirmed_count = len([item for item in coverage_items_for_req if item.get("review_status") == "Confirmed"])
strategy_count = len([item for item in ps["strategy_items"] if item["req_id"] == requirement["req_id"]])

stat1, stat2, stat3 = st.columns(3)
with stat1:
    st.metric("已生成覆盖项", len(coverage_items_for_req))
with stat2:
    st.metric("已确认覆盖项", confirmed_count)
with stat3:
    st.metric("策略已映射", strategy_count)

action1, action2 = st.columns([1, 1])
with action1:
    if st.button("生成此需求的覆盖项", type="primary"):
        generated = regenerate_coverage_for_requirement(ps, requirement, parsed_req, risk_item, use_llm, llm_client)
        save_state(ps)
        st.success(f"已生成 {generated} 条覆盖项")
        st.rerun()
with action2:
    if st.button("批量确认所有 Draft 覆盖项"):
        st.session_state["confirm_batch_cov"] = True

if st.session_state.get("confirm_batch_cov"):
    st.warning("将把当前需求下所有 Draft 覆盖项确认，并同步创建/更新策略项。再次点击确认。")
    if st.button("确认批量确认当前需求覆盖项", key="confirm_cov_btn"):
        changed = 0
        for item in ps["coverage_items"]:
            if item["req_id"] != requirement["req_id"] or item.get("review_status") != "Draft":
                continue
            old_item = deepcopy(item)
            item["review_status"] = "Confirmed"
            item["last_edited_by"] = "human"
            old_strategy = deepcopy(find_strategy_by_cov(ps, item["cov_id"])) if find_strategy_by_cov(ps, item["cov_id"]) else None
            strategy = find_strategy_by_cov(ps, item["cov_id"])
            selected = strategy["selected_technique"] if strategy else auto_recommend_technique(item)
            rationale = strategy["technique_rationale"] if strategy else "Batch confirm with auto recommendation"
            notes = strategy["generation_notes"] if strategy else ""
            strategy_record = sync_strategy_for_coverage(ps, item, selected, rationale, notes, review_status="Confirmed")
            log_change(ps, "coverage_item", item["cov_id"], "Confirmed", "record", old_item, item, "human", "Batch confirm")
            log_change(ps, "strategy_item", strategy_record["strategy_id"], "Confirmed", "record", old_strategy, strategy_record, "human", "Batch confirm sync")
            changed += 1
        save_state(ps)
        st.session_state["confirm_batch_cov"] = False
        st.success(f"已确认 {changed} 条覆盖项")
        st.rerun()

gaps = check_coverage_gaps(parsed_req, coverage_items_for_req)
if gaps:
    with st.expander(f"⚠️ 发现 {len(gaps)} 个可能的覆盖缺口", expanded=True):
        for gap in gaps:
            st.warning(gap)

st.subheader("覆盖项列表")
if not coverage_items_for_req:
    st.info("当前需求还没有覆盖项。")
else:
    for item in coverage_items_for_req:
        badge_color = CATEGORY_BADGE_COLORS.get(item["category"], "#E5E7EB")
        tech_color = TECHNIQUE_COLORS.get(item.get("suggested_technique", "EP"), "#E5E7EB")
        label = (
            f"{item['cov_id']} "
            f"[{item['category']}] {item['title']} "
            f"[{item['review_status']}] [{item.get('suggested_technique', 'EP')}]"
        )
        if st.button(label, key=f"cov_btn_{item['cov_id']}", use_container_width=True):
            st.session_state["selected_cov_id"] = item["cov_id"]
        st.markdown(
            f"<div style='margin:-8px 0 8px 0;font-size:12px;'>"
            f"<span style='background:{badge_color};padding:2px 6px;border-radius:12px;margin-right:6px;'>{item['category']}</span>"
            f"<span style='background:{tech_color};padding:2px 6px;border-radius:12px;'>{item.get('suggested_technique', 'EP')}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

if st.button("＋ 手动添加覆盖项"):
    st.session_state["show_manual_cov_form"] = True

if st.session_state.get("show_manual_cov_form"):
    with st.form("manual_cov_form"):
        manual_title = st.text_input("标题 *")
        manual_description = st.text_area("描述 *", height=100)
        manual_category = st.selectbox("类别", COVERAGE_CATEGORIES)
        manual_focus = st.text_input("测试重点")
        manual_partitions = st.text_input("等价类划分（逗号分隔）")
        manual_boundaries = st.text_input("边界值（逗号分隔）")
        manual_submit = st.form_submit_button("保存手动覆盖项", type="primary")
    if manual_submit:
        if not manual_title.strip() or not manual_description.strip():
            st.error("标题和描述为必填项")
            st.stop()
        new_cov = dataclass_to_dict(
            CoverageItem(
                cov_id=generate_coverage_id(ps),
                req_id=requirement["req_id"],
                parsed_id=parsed_req["parsed_id"],
                risk_id=risk_item["risk_id"],
                category=manual_category,
                title=manual_title.strip(),
                description=manual_description.strip(),
                test_focus=manual_focus.strip(),
                input_partitions=[item.strip() for item in manual_partitions.split(",") if item.strip()],
                boundary_values=[item.strip() for item in manual_boundaries.split(",") if item.strip()],
                suggested_technique=auto_recommend_technique({"category": manual_category}),
                risk_level=risk_item["risk_level"],
                review_status="Draft",
                last_edited_by="human",
            )
        )
        ps["coverage_items"].append(new_cov)
        log_change(ps, "coverage_item", new_cov["cov_id"], "Created", "record", None, new_cov, "human", "Manual coverage creation")
        save_state(ps)
        st.session_state["show_manual_cov_form"] = False
        st.success(f"已创建 {new_cov['cov_id']}")
        st.rerun()

selected_cov_id = st.session_state.get("selected_cov_id")
selected_cov = find_coverage(ps, selected_cov_id) if selected_cov_id else None

if selected_cov is None:
    st.info("点击上方某条覆盖项后可在下方编辑。")
    st.stop()

strategy = find_strategy_by_cov(ps, selected_cov["cov_id"])
selected_default = strategy["selected_technique"] if strategy else auto_recommend_technique(selected_cov)

st.subheader("覆盖项编辑器")
st.text_input("覆盖项 ID", value=selected_cov["cov_id"], disabled=True)
st.text_input("关联需求", value=selected_cov["req_id"], disabled=True)

title = st.text_input("标题", value=selected_cov.get("title", ""), key=f"cov_title_{selected_cov['cov_id']}")
description = st.text_area("描述", value=selected_cov.get("description", ""), height=100, key=f"cov_desc_{selected_cov['cov_id']}")
category = st.selectbox(
    "类别",
    COVERAGE_CATEGORIES,
    index=COVERAGE_CATEGORIES.index(selected_cov.get("category", "Input")),
    key=f"cov_category_{selected_cov['cov_id']}",
)
test_focus = st.text_input("测试重点", value=selected_cov.get("test_focus", ""), key=f"cov_focus_{selected_cov['cov_id']}")
input_partitions = edit_string_list(selected_cov.get("input_partitions", []), key=f"cov_partitions_{selected_cov['cov_id']}", label="等价类划分")
boundary_values = edit_string_list(selected_cov.get("boundary_values", []), key=f"cov_boundaries_{selected_cov['cov_id']}", label="边界值")

st.markdown("### 策略映射")
recommended = auto_recommend_technique({"category": category})
st.write(f"推荐技术（LLM/规则建议）: `{recommended}`")

tech_options = TECHNIQUES + ["Custom"]
current_option = selected_default if selected_default in TECHNIQUES else "Custom"
selected_option = st.selectbox("最终选定技术", tech_options, index=tech_options.index(current_option), key=f"tech_option_{selected_cov['cov_id']}")
custom_technique = ""
if selected_option == "Custom":
    custom_technique = st.text_input("自定义技术", value="" if selected_default in TECHNIQUES else selected_default, key=f"custom_tech_{selected_cov['cov_id']}")
selected_technique = custom_technique.strip() if selected_option == "Custom" else selected_option

technique_rationale = st.text_area(
    "选择理由",
    value=strategy.get("technique_rationale", "") if strategy else "",
    height=90,
    key=f"tech_rationale_{selected_cov['cov_id']}",
)
generation_notes = st.text_area(
    "生成备注",
    value=strategy.get("generation_notes", "") if strategy else "",
    height=90,
    key=f"tech_notes_{selected_cov['cov_id']}",
)

btn1, btn2, btn3, btn4 = st.columns(4)
save_clicked = btn1.button("Save", type="primary")
confirm_clicked = btn2.button("Confirm")
reject_clicked = btn3.button("Reject")
delete_clicked = btn4.button("删除此覆盖项")

if save_clicked or confirm_clicked or reject_clicked:
    old_cov = deepcopy(selected_cov)
    old_strategy = deepcopy(strategy) if strategy else None
    selected_cov["title"] = title.strip()
    selected_cov["description"] = description.strip()
    selected_cov["category"] = category
    selected_cov["test_focus"] = test_focus.strip()
    selected_cov["input_partitions"] = input_partitions
    selected_cov["boundary_values"] = boundary_values
    selected_cov["suggested_technique"] = recommended
    selected_cov["last_edited_by"] = "human"

    action = "Edited"
    strategy_status = "Draft"
    if confirm_clicked:
        selected_cov["review_status"] = "Confirmed"
        action = "Confirmed"
        strategy_status = "Confirmed"
    elif reject_clicked:
        selected_cov["review_status"] = "Rejected"
        action = "Rejected"
        strategy_status = "Rejected"

    strategy_record = sync_strategy_for_coverage(
        ps,
        selected_cov,
        selected_technique or recommended,
        technique_rationale.strip(),
        generation_notes.strip(),
        review_status=strategy_status,
    )
    log_change(ps, "coverage_item", selected_cov["cov_id"], action, "record", old_cov, selected_cov, "human", "Manual coverage edit")
    log_change(ps, "strategy_item", strategy_record["strategy_id"], action, "record", old_strategy, strategy_record, "human", "Coverage-strategy sync")
    save_state(ps)
    st.success(f"{selected_cov['cov_id']} 已保存")
    st.rerun()

if delete_clicked:
    st.session_state["confirm_delete_cov"] = True

if st.session_state.get("confirm_delete_cov"):
    st.error("再次点击确认后会删除该覆盖项及其策略映射。")
    if st.button("确认删除覆盖项", key=f"confirm_delete_cov_{selected_cov['cov_id']}"):
        old_cov = deepcopy(selected_cov)
        ps["coverage_items"] = [item for item in ps["coverage_items"] if item["cov_id"] != selected_cov["cov_id"]]
        deleted_strategy = find_strategy_by_cov(ps, selected_cov["cov_id"])
        ps["strategy_items"] = [item for item in ps["strategy_items"] if item["cov_id"] != selected_cov["cov_id"]]
        log_change(ps, "coverage_item", old_cov["cov_id"], "Deleted", "record", old_cov, None, "human", "Deleted from coverage page")
        if deleted_strategy:
            log_change(ps, "strategy_item", deleted_strategy["strategy_id"], "Deleted", "record", deleted_strategy, None, "human", "Cascade delete with coverage item")
        save_state(ps)
        st.session_state["confirm_delete_cov"] = False
        st.session_state["selected_cov_id"] = None
        st.success("覆盖项已删除")
        st.rerun()
