from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any, Dict, List

import streamlit as st

from core.coverage_builder import build_coverage_items, check_coverage_gaps
from core.data_model import COVERAGE_CATEGORIES, RECORD_REVIEW_STATUS, TECHNIQUES, CoverageItem, dataclass_to_dict
from core.llm_client import LlmClient, load_config
from core.state_manager import (
    find_risk_by_req_id,
    find_requirement,
    find_strategy_by_cov,
    find_suite,
    generate_coverage_id,
    get_state,
    save_state,
)
from core.strategy_planner import auto_recommend_technique, sync_strategy_for_coverage
from core.test_suite_manager import (
    coverage_progress_by_suite,
    ensure_default_test_suites,
    sync_coverage_suite_ids,
)
from utils.change_tracker import log_change
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


def edit_list_block(values: List[str], key: str, label: str, placeholder: str = "") -> List[str]:
    text_value = "\n".join(values or [])
    edited = st.text_area(
        label,
        value=text_value,
        height=110,
        key=key,
        placeholder=placeholder or "One item per line",
    )
    return [line.strip() for line in edited.splitlines() if line.strip()]


def next_coverage_number(ps: Dict[str, Any]) -> int:
    max_num = 0
    for item in ps["coverage_items"]:
        raw = str(item.get("cov_id", ""))
        if raw.startswith("COV-"):
            suffix = raw.split("-", 1)[1]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return max_num + 1


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


def build_coverage_overview_rows(coverage_items: List[Dict[str, Any]], ps: Dict[str, Any]) -> List[Dict[str, str]]:
    rows = []
    for item in coverage_items:
        strategy = find_strategy_by_cov(ps, item["cov_id"])
        suite_names = [find_suite(ps, suite_id).get("name", suite_id) for suite_id in item.get("suite_ids", []) if find_suite(ps, suite_id)]
        rows.append(
            {
                "coverage_id": item.get("cov_id", ""),
                "requirement_id": item.get("req_id", ""),
                "category": item.get("category", ""),
                "title": item.get("title", ""),
                "归属套件": " | ".join(suite_names) if suite_names else "",
                "selected_technique": strategy.get("selected_technique", "") if strategy else "",
                "review_status": item.get("review_status", ""),
            }
        )
    return rows


SUITE_MORANDI_COLORS = [
    "#C8D5C0",
    "#D8C5B1",
    "#C7CDD9",
    "#D5C0C8",
    "#C9D2C3",
    "#D7CCB8",
    "#BEC7D0",
    "#D3CABA",
]


def render_coverage_page_styles() -> None:
    st.markdown(
        """
        <style>
        .suite-chip-wrap {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            padding: 2px 0;
        }
        .suite-chip {
            display: inline-flex;
            align-items: center;
            padding: 5px 10px;
            border-radius: 999px;
            color: #4F4A41;
            font-size: 0.82rem;
            font-weight: 600;
            line-height: 1.2;
            border: 1px solid rgba(95, 83, 62, 0.08);
            white-space: nowrap;
        }
        .suite-chip-empty {
            background: #F4F0E7;
            color: #8D8578;
        }
        div[data-baseweb="select"] span[data-baseweb="tag"] {
            background: #FFF5DA !important;
            border: 1px solid #E7D7A6 !important;
            color: #7B5A24 !important;
        }
        div[data-baseweb="select"] span[data-baseweb="tag"] * {
            color: #7B5A24 !important;
            fill: #7B5A24 !important;
        }
        .coverage-grid-head {
            color: #7A7F8E;
            font-size: 0.92rem;
            font-weight: 600;
            padding-bottom: 6px;
        }
        .coverage-grid-cell {
            color: #2F3447;
            font-size: 0.98rem;
            line-height: 1.55;
            word-break: break-word;
            padding-top: 4px;
            padding-bottom: 4px;
        }
        .coverage-summary-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin: 10px 0 18px;
        }
        .coverage-summary-card {
            border: 1px solid rgba(145, 120, 74, 0.14);
            border-radius: 18px;
            padding: 14px 18px;
            background: rgba(255, 255, 255, 0.82);
        }
        .coverage-summary-label {
            color: #7A7F8E;
            font-size: 0.92rem;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .coverage-summary-value {
            color: #2F3447;
            font-size: 1.55rem;
            font-weight: 700;
            line-height: 1;
        }
        div[data-testid="stMetric"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_suite_color_map(ps: Dict[str, Any]) -> Dict[str, str]:
    suites = ps.get("test_suites", [])
    return {
        suite.get("suite_id", ""): SUITE_MORANDI_COLORS[index % len(SUITE_MORANDI_COLORS)]
        for index, suite in enumerate(suites)
    }


def build_suite_chip_html(ps: Dict[str, Any], suite_ids: List[str], suite_color_map: Dict[str, str]) -> str:
    chips: List[str] = []
    for suite_id in suite_ids:
        suite = find_suite(ps, suite_id)
        if not suite:
            continue
        label = suite.get("suite_id", suite_id)
        chips.append(
            f"<span class='suite-chip' style='background:{suite_color_map.get(suite_id, '#F4F0E7')};'>{escape(label)}</span>"
        )
    if not chips:
        return "<div class='suite-chip-wrap'><span class='suite-chip suite-chip-empty'>未分配</span></div>"
    if not chips:
        chips.append("<span class='suite-chip suite-chip-empty'>未分配</span>")
    return "<div class='suite-chip-wrap'>" + "".join(chips) + "</div>"


def render_coverage_overview_table(
    coverage_items: List[Dict[str, Any]],
    ps: Dict[str, Any],
    suite_color_map: Dict[str, str],
) -> None:
    column_widths = [1.05, 1.0, 1.15, 0.9, 3.2, 1.8, 1.1]
    headers = [
        "归属套件",
        "coverage_id",
        "requirement_id",
        "category",
        "title",
        "technique",
        "status",
    ]
    headers[0] = "suite"

    with st.container(border=True):
        header_cols = st.columns(column_widths)
        for col, title in zip(header_cols, headers):
            with col:
                st.markdown(f"<div class='coverage-grid-head'>{escape(title)}</div>", unsafe_allow_html=True)

        st.divider()

        for index, item in enumerate(coverage_items):
            strategy = find_strategy_by_cov(ps, item["cov_id"])
            row_cols = st.columns(column_widths)
            with row_cols[0]:
                st.markdown(build_suite_chip_html(ps, item.get("suite_ids", []), suite_color_map), unsafe_allow_html=True)
            with row_cols[1]:
                st.markdown(f"<div class='coverage-grid-cell'>{escape(item.get('cov_id', ''))}</div>", unsafe_allow_html=True)
            with row_cols[2]:
                st.markdown(f"<div class='coverage-grid-cell'>{escape(item.get('req_id', ''))}</div>", unsafe_allow_html=True)
            with row_cols[3]:
                st.markdown(f"<div class='coverage-grid-cell'>{escape(item.get('category', ''))}</div>", unsafe_allow_html=True)
            with row_cols[4]:
                st.markdown(f"<div class='coverage-grid-cell'>{escape(item.get('title', ''))}</div>", unsafe_allow_html=True)
            with row_cols[5]:
                technique = (strategy.get("selected_technique", "") if strategy else "") or item.get("suggested_technique", "") or auto_recommend_technique(item)
                st.markdown(f"<div class='coverage-grid-cell'>{escape(technique)}</div>", unsafe_allow_html=True)
            with row_cols[6]:
                review_status = item.get("review_status", "") or "Draft"
                st.markdown(f"<div class='coverage-grid-cell'>{escape(review_status)}</div>", unsafe_allow_html=True)
            if index != len(coverage_items) - 1:
                st.divider()
    return


def render_global_coverage_summary(total_coverage: int, total_confirmed: int, total_mapped: int) -> None:
    st.markdown(
        """
        <div class="coverage-summary-strip">
            <div class="coverage-summary-card">
                <div class="coverage-summary-label">已生成覆盖项</div>
                <div class="coverage-summary-value">{total_coverage}</div>
            </div>
            <div class="coverage-summary-card">
                <div class="coverage-summary-label">已确认覆盖项</div>
                <div class="coverage-summary-value">{total_confirmed}</div>
            </div>
            <div class="coverage-summary-card">
                <div class="coverage-summary-label">策略已映射</div>
                <div class="coverage-summary-value">{total_mapped}</div>
            </div>
        </div>
        """.format(
            total_coverage=total_coverage,
            total_confirmed=total_confirmed,
            total_mapped=total_mapped,
        ),
        unsafe_allow_html=True,
    )
    return

    rows: List[str] = []
    for item in coverage_items:
        strategy = find_strategy_by_cov(ps, item["cov_id"])
        rows.append(
            """
            <tr>
                <td class="suite-cell">{suite_html}</td>
                <td>{cov_id}</td>
                <td>{req_id}</td>
                <td>{category}</td>
                <td class="title-cell">{title}</td>
                <td>{selected_technique}</td>
                <td>{review_status}</td>
            </tr>
            """.format(
                suite_html=build_suite_chip_html(ps, item.get("suite_ids", []), suite_color_map),
                cov_id=escape(item.get("cov_id", "")),
                req_id=escape(item.get("req_id", "")),
                category=escape(item.get("category", "")),
                title=escape(item.get("title", "")),
                selected_technique=escape(strategy.get("selected_technique", "") if strategy else ""),
                review_status=escape(item.get("review_status", "")),
            )
        )

    st.markdown(
        """
        <div class="suite-overview-table">
            <table>
                <thead>
                    <tr>
                        <th>归属套件</th>
                        <th>coverage_id</th>
                        <th>requirement_id</th>
                        <th>category</th>
                        <th>title</th>
                        <th>selected_technique</th>
                        <th>review_status</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """.format(rows="".join(rows)),
        unsafe_allow_html=True,
    )


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
    default_suite_ids = [
        suite.get("suite_id", "")
        for suite in ps.get("test_suites", [])
        if requirement["req_id"] in suite.get("requirement_ids", [])
    ]
    for item in generated:
        item["suite_ids"] = list(default_suite_ids)
        ps["coverage_items"].append(item)
        log_change(ps, "coverage_item", item["cov_id"], "Created", "record", None, item, "llm", "Coverage generation")
    return len(generated)


def regenerate_coverage_for_all_requirements(
    ps: Dict[str, Any],
    eligible_requirements: List[tuple[int, Dict[str, Any], Dict[str, Any], Dict[str, Any]]],
    use_llm: bool,
    llm_client: LlmClient,
) -> Dict[str, int]:
    generated_total = 0
    requirement_total = 0
    for _, requirement, parsed_req, risk_item in eligible_requirements:
        generated_total += regenerate_coverage_for_requirement(
            ps,
            requirement,
            parsed_req,
            risk_item,
            use_llm,
            llm_client,
        )
        requirement_total += 1
    return {"generated_total": generated_total, "requirement_total": requirement_total}


def render_requirement_context(requirement: Dict[str, Any], parsed_req: Dict[str, Any], risk_item: Dict[str, Any]) -> None:
    info1, info2 = st.columns(2)
    with info1:
        st.markdown("#### Selected Requirement")
        st.write(parsed_req.get("summary") or requirement.get("raw_text", ""))
    with info2:
        st.markdown("#### Risk Context")
        st.write(f"{risk_item['risk_title']} | {risk_item['risk_level']} / {risk_item['risk_score']}")
        st.write(risk_item.get("risk_summary", ""))


def switch_page_safe(target: str, fallback_message: str) -> None:
    if hasattr(st, "switch_page"):
        st.switch_page(target)
    else:
        st.success(fallback_message)


st.set_page_config(page_title="Coverage & Strategy", layout="wide", page_icon=":triangular_ruler:")
apply_reference_theme()
render_coverage_page_styles()

ps = get_state()
use_llm = bool(st.session_state.get("use_llm", False))
llm_client = LlmClient(load_config())

auto_changed = ensure_default_test_suites(ps)
auto_changed = sync_coverage_suite_ids(ps) or auto_changed
if auto_changed:
    save_state(ps)

with st.sidebar:
    render_workflow_sidebar("Coverage & Strategy")

render_hero(
    "Coverage Planning",
    "Coverage & Strategy",
    "Generate coverage items, assign them to suites, and confirm the coverage-to-strategy mapping before suite-level detail design.",
)

eligible_requirements = []
for parsed_req in ps["parsed_requirements"]:
    if parsed_req.get("review_status") != "Approved":
        continue
    risk_item = find_risk_by_req_id(ps, parsed_req["req_id"])
    if risk_item is None:
        continue
    requirement = find_requirement(ps, parsed_req["req_id"])
    if requirement is None:
        continue
    eligible_requirements.append((risk_item["risk_score"], requirement, parsed_req, risk_item))

eligible_requirements.sort(key=lambda item: item[0], reverse=True)

if not eligible_requirements:
    st.info("No approved structured requirements with risk context yet. Complete structured review and risk assessment first.")
    st.stop()

labels = [
    f"{req['req_id']} - {req['title']} [{risk['risk_level']} / {risk['risk_score']}]"
    for _, req, _, risk in eligible_requirements
]
label_map = {
    f"{req['req_id']} - {req['title']} [{risk['risk_level']} / {risk['risk_score']}]": (req, parsed, risk)
    for _, req, parsed, risk in eligible_requirements
}

risk_score_by_req = {req["req_id"]: score for score, req, _, _ in eligible_requirements}
suite_color_map = build_suite_color_map(ps)
all_coverage_items = sorted(
    ps["coverage_items"],
    key=lambda item: (
        -risk_score_by_req.get(item.get("req_id", ""), -1),
        item.get("req_id", ""),
        item.get("cov_id", ""),
    ),
)
total_coverage_count = len(all_coverage_items)
total_confirmed_count = len([item for item in all_coverage_items if item.get("review_status") == "Confirmed"])
total_strategy_count = len([item for item in ps["strategy_items"] if item.get("cov_id")])

render_global_coverage_summary(total_coverage_count, total_confirmed_count, total_strategy_count)

with st.expander(f"所有覆盖项 ({total_coverage_count})", expanded=False):
    if all_coverage_items:
        render_coverage_overview_table(all_coverage_items, ps, suite_color_map)
    else:
        st.info("当前还没有覆盖项。")

selected_label = st.selectbox("Requirement Selector (Sorted by Risk)", labels)
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

render_requirement_context(requirement, parsed_req, risk_item)

action1, action2, action3 = st.columns([1, 1, 1])
with action1:
    if st.button("生成此需求的覆盖项", type="primary", use_container_width=True):
        generated = regenerate_coverage_for_requirement(ps, requirement, parsed_req, risk_item, use_llm, llm_client)
        save_state(ps)
        st.success(f"已生成 {generated} 条覆盖项。")
        st.rerun()
with action3:
    if st.button("批量生成所有需求覆盖项", type="secondary", use_container_width=True):
        result = regenerate_coverage_for_all_requirements(ps, eligible_requirements, use_llm, llm_client)
        save_state(ps)
        st.success(f"已为 {result['requirement_total']} 个需求批量生成 {result['generated_total']} 条覆盖项。")
        st.rerun()
with action2:
    if st.button("批量确认所有 Draft 覆盖项", type="secondary", use_container_width=True):
        st.session_state["confirm_batch_cov"] = True

if st.session_state.get("confirm_batch_cov"):
    st.warning("这会确认当前需求下所有 Draft 覆盖项，并同步更新对应策略。")
    if st.button("确认批量确认当前需求覆盖项", key="confirm_cov_btn", type="secondary", use_container_width=True):
        changed = 0
        for item in ps["coverage_items"]:
            if item["req_id"] != requirement["req_id"] or item.get("review_status") != "Draft":
                continue
            old_item = deepcopy(item)
            item["review_status"] = "Confirmed"
            item["last_edited_by"] = "human"
            strategy = find_strategy_by_cov(ps, item["cov_id"])
            old_strategy = deepcopy(strategy) if strategy else None
            selected = strategy["selected_technique"] if strategy else auto_recommend_technique(item)
            rationale = strategy["technique_rationale"] if strategy else "Batch confirm with auto recommendation"
            notes = strategy["generation_notes"] if strategy else ""
            strategy_record = sync_strategy_for_coverage(ps, item, selected, rationale, notes, review_status="Confirmed")
            log_change(ps, "coverage_item", item["cov_id"], "Confirmed", "record", old_item, item, "human", "Batch confirm")
            log_change(ps, "strategy_item", strategy_record["strategy_id"], "Confirmed", "record", old_strategy, strategy_record, "human", "Batch confirm sync")
            changed += 1
        save_state(ps)
        st.session_state["confirm_batch_cov"] = False
        st.success(f"已确认 {changed} 条覆盖项。")
        st.rerun()

gaps = check_coverage_gaps(parsed_req, coverage_items_for_req)
if gaps:
    with st.expander(f"⚠️ 发现 {len(gaps)} 个可能的覆盖缺口", expanded=True):
        for gap in gaps:
            st.warning(gap)

st.markdown("### Coverage Items")
suite_color_map = build_suite_color_map(ps)
suite_options = {f"{item['suite_id']} {item['name']}": item["suite_id"] for item in ps.get("test_suites", [])}
if coverage_items_for_req:
    render_coverage_overview_table(coverage_items_for_req, ps, suite_color_map)
else:
    st.info("当前需求还没有覆盖项。")

suite_options = {f"{item['suite_id']} {item['name']}": item["suite_id"] for item in ps.get("test_suites", [])}
if False and coverage_items_for_req and suite_options:
    st.markdown("#### 归属套件")
    with st.form("suite_assignment_form"):
        header_cols = st.columns([1.1, 1.1, 1, 2.2, 2.3])
        header_titles = ["coverage_id", "requirement_id", "category", "title", "归属套件"]
        for col, title in zip(header_cols, header_titles):
            with col:
                st.caption(title)

        selected_assignments: Dict[str, List[str]] = {}
        for item in coverage_items_for_req:
            row_cols = st.columns([1.1, 1.1, 1, 2.2, 2.3])
            with row_cols[0]:
                st.write(item.get("cov_id", ""))
            with row_cols[1]:
                st.write(item.get("req_id", ""))
            with row_cols[2]:
                st.write(item.get("category", ""))
            with row_cols[3]:
                st.write(item.get("title", ""))
            with row_cols[4]:
                default_labels = [label for label, suite_id in suite_options.items() if suite_id in item.get("suite_ids", [])]
                selected_labels = st.multiselect(
                    "归属套件",
                    options=list(suite_options.keys()),
                    default=default_labels,
                    key=f"suite_assignment_{item['cov_id']}",
                    label_visibility="collapsed",
                )
                selected_assignments[item["cov_id"]] = [suite_options[label] for label in selected_labels]

        assign_submit = st.form_submit_button("保存归属套件", type="secondary", use_container_width=True)

    if assign_submit:
        changed = 0
        for item in ps["coverage_items"]:
            if item.get("cov_id") not in selected_assignments:
                continue
            new_suite_ids = selected_assignments[item["cov_id"]]
            if item.get("suite_ids", []) != new_suite_ids:
                old_value = deepcopy(item)
                item["suite_ids"] = new_suite_ids
                item["last_edited_by"] = "human"
                log_change(ps, "coverage_item", item["cov_id"], "Edited", "record", old_value, item, "human", "Updated suite assignment")
                changed += 1
        save_state(ps)
        st.success(f"已更新 {changed} 条覆盖项的套件归属。")
        st.rerun()

with st.expander("+ 手动添加覆盖项", expanded=False):
    manual_title = st.text_input("标题 *", key="manual_cov_title")
    manual_description = st.text_area("描述 *", height=100, key="manual_cov_description")
    manual_category = st.selectbox("类别", COVERAGE_CATEGORIES, key="manual_cov_category")
    manual_focus = st.text_input("测试重点", key="manual_cov_focus")
    manual_partitions = st.text_area("等价类划分", height=90, key="manual_cov_partitions", placeholder="每行一条")
    manual_boundaries = st.text_area("边界值", height=90, key="manual_cov_boundaries", placeholder="每行一条")
    default_suite_labels = [label for label, suite_id in suite_options.items() if requirement["req_id"] in next((item.get("requirement_ids", []) for item in ps["test_suites"] if item["suite_id"] == suite_id), [])]
    manual_suite_labels = st.multiselect("归属套件", options=list(suite_options.keys()), default=default_suite_labels)
    if st.button("保存手动覆盖项", key="manual_cov_submit", type="secondary"):
        if not manual_title.strip() or not manual_description.strip():
            st.error("标题和描述为必填项。")
        else:
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
                    input_partitions=[item.strip() for item in manual_partitions.splitlines() if item.strip()],
                    boundary_values=[item.strip() for item in manual_boundaries.splitlines() if item.strip()],
                    suggested_technique=auto_recommend_technique({"category": manual_category}),
                    risk_level=risk_item["risk_level"],
                    review_status="Draft",
                    last_edited_by="human",
                    suite_ids=[suite_options[label] for label in manual_suite_labels],
                )
            )
            ps["coverage_items"].append(new_cov)
            log_change(ps, "coverage_item", new_cov["cov_id"], "Created", "record", None, new_cov, "human", "Manual coverage creation")
            save_state(ps)
            st.success(f"已创建 {new_cov['cov_id']}")
            st.rerun()

if coverage_items_for_req:
    st.markdown("### Coverage Item Editor")

status_rank = {"Draft": 0, "Modified": 1, "Confirmed": 2, "Rejected": 3, "Needs Discussion": 4}
sorted_coverage_items = sorted(
    coverage_items_for_req,
    key=lambda item: (status_rank.get(item.get("review_status", "Draft"), 99), item.get("cov_id", "")),
)

for item in sorted_coverage_items:
    strategy = find_strategy_by_cov(ps, item["cov_id"])
    selected_default = strategy["selected_technique"] if strategy else auto_recommend_technique(item)
    suite_names = [find_suite(ps, suite_id).get("name", suite_id) for suite_id in item.get("suite_ids", []) if find_suite(ps, suite_id)]
    expander_title = (
        f"{item['cov_id']} - {item['category']} - {item['title']} "
        f"[{item.get('review_status', 'Draft')}]"
    )

    with st.expander(expander_title, expanded=item.get("review_status") == "Draft"):
        st.caption(
            f"Risk priority: {item.get('risk_level', risk_item['risk_level'])} | "
            f"requirement {item['req_id']} | suites {', '.join(suite_names) or 'None'}"
        )

        meta1, meta2, meta3 = st.columns(3)
        with meta1:
            st.text_input("Coverage ID", value=item["cov_id"], disabled=True, key=f"cov_id_{item['cov_id']}")
        with meta2:
            st.text_input("Requirement ID", value=item["req_id"], disabled=True, key=f"req_id_{item['cov_id']}")
        with meta3:
            st.text_input("Risk ID", value=item["risk_id"], disabled=True, key=f"risk_id_{item['cov_id']}")

        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            title = st.text_input("Title", value=item.get("title", ""), key=f"cov_title_{item['cov_id']}")
        with row1_col2:
            category = st.selectbox(
                "Category",
                COVERAGE_CATEGORIES,
                index=COVERAGE_CATEGORIES.index(item.get("category", "Input")) if item.get("category", "Input") in COVERAGE_CATEGORIES else 0,
                key=f"cov_category_{item['cov_id']}",
            )

        description = st.text_area("Description", value=item.get("description", ""), height=110, key=f"cov_desc_{item['cov_id']}")
        test_focus = st.text_area("Test Focus", value=item.get("test_focus", ""), height=90, key=f"cov_focus_{item['cov_id']}")

        part_col1, part_col2 = st.columns(2)
        with part_col1:
            input_partitions = edit_list_block(item.get("input_partitions", []), key=f"cov_partitions_{item['cov_id']}", label="Input Partitions")
        with part_col2:
            boundary_values = edit_list_block(item.get("boundary_values", []), key=f"cov_boundaries_{item['cov_id']}", label="Boundary Values")

        suite_multiselect = st.multiselect(
            "归属套件",
            options=list(suite_options.keys()),
            default=[label for label, suite_id in suite_options.items() if suite_id in item.get("suite_ids", [])],
            key=f"cov_suite_ids_{item['cov_id']}",
        )

        st.markdown("##### Strategy Mapping")
        recommended = auto_recommend_technique({"category": category})
        map_col1, map_col2 = st.columns(2)
        with map_col1:
            st.text_input("Recommended Technique", value=recommended, disabled=True, key=f"cov_recommended_{item['cov_id']}")
        with map_col2:
            review_status = st.selectbox(
                "Review Status",
                RECORD_REVIEW_STATUS,
                index=RECORD_REVIEW_STATUS.index(item.get("review_status", "Draft")) if item.get("review_status", "Draft") in RECORD_REVIEW_STATUS else 0,
                key=f"cov_status_{item['cov_id']}",
            )

        tech_options = TECHNIQUES + ["Custom"]
        current_option = selected_default if selected_default in TECHNIQUES else "Custom"
        tech_col1, tech_col2 = st.columns(2)
        with tech_col1:
            selected_option = st.selectbox("Selected Technique", tech_options, index=tech_options.index(current_option), key=f"tech_option_{item['cov_id']}")
        with tech_col2:
            custom_technique = ""
            if selected_option == "Custom":
                custom_technique = st.text_input("Custom Technique", value="" if selected_default in TECHNIQUES else selected_default, key=f"custom_tech_{item['cov_id']}")
        selected_technique = custom_technique.strip() if selected_option == "Custom" else selected_option

        technique_rationale = st.text_area("Technique Rationale", value=strategy.get("technique_rationale", "") if strategy else "", height=90, key=f"tech_rationale_{item['cov_id']}")
        generation_notes = st.text_area("Generation Notes", value=strategy.get("generation_notes", "") if strategy else "", height=90, key=f"tech_notes_{item['cov_id']}")

        btn1, btn2, btn3, btn4 = st.columns(4)
        save_clicked = btn1.button("Save", key=f"save_cov_{item['cov_id']}", type="primary")
        confirm_clicked = btn2.button("Confirm", key=f"confirm_cov_{item['cov_id']}", type="secondary")
        reject_clicked = btn3.button("Reject", key=f"reject_cov_{item['cov_id']}", type="secondary")
        delete_clicked = btn4.button("Delete", key=f"delete_cov_{item['cov_id']}", type="secondary")

        if save_clicked or confirm_clicked or reject_clicked:
            old_cov = deepcopy(item)
            old_strategy = deepcopy(strategy) if strategy else None
            item["title"] = title.strip()
            item["description"] = description.strip()
            item["category"] = category
            item["test_focus"] = test_focus.strip()
            item["input_partitions"] = input_partitions
            item["boundary_values"] = boundary_values
            item["suggested_technique"] = recommended
            item["suite_ids"] = [suite_options[label] for label in suite_multiselect]
            item["last_edited_by"] = "human"

            action = "Edited"
            strategy_status = "Draft"
            if confirm_clicked:
                item["review_status"] = "Confirmed"
                action = "Confirmed"
                strategy_status = "Confirmed"
            elif reject_clicked:
                item["review_status"] = "Rejected"
                action = "Rejected"
                strategy_status = "Rejected"
            else:
                item["review_status"] = review_status
                if review_status == "Modified":
                    action = "Modified"

            strategy_record = sync_strategy_for_coverage(
                ps,
                item,
                selected_technique or recommended,
                technique_rationale.strip(),
                generation_notes.strip(),
                review_status=strategy_status if action in {"Confirmed", "Rejected"} else item["review_status"],
            )
            log_change(ps, "coverage_item", item["cov_id"], action, "record", old_cov, item, "human", "Manual coverage edit")
            log_change(ps, "strategy_item", strategy_record["strategy_id"], action, "record", old_strategy, strategy_record, "human", "Coverage-strategy sync")
            save_state(ps)
            st.success(f"{item['cov_id']} updated to {item['review_status']}.")
            st.rerun()

        confirm_delete_key = f"confirm_delete_cov_{item['cov_id']}"
        if delete_clicked:
            st.session_state[confirm_delete_key] = True

        if st.session_state.get(confirm_delete_key):
            st.warning("Deleting this coverage item will also remove its mapped strategy.")
            if st.button("确认删除覆盖项", key=f"confirm_delete_button_{item['cov_id']}", type="secondary"):
                old_cov = deepcopy(item)
                deleted_strategy = find_strategy_by_cov(ps, item["cov_id"])
                ps["coverage_items"] = [entry for entry in ps["coverage_items"] if entry["cov_id"] != item["cov_id"]]
                ps["strategy_items"] = [entry for entry in ps["strategy_items"] if entry["cov_id"] != item["cov_id"]]
                log_change(ps, "coverage_item", old_cov["cov_id"], "Deleted", "record", old_cov, None, "human", "Deleted from coverage page")
                if deleted_strategy:
                    log_change(ps, "strategy_item", deleted_strategy["strategy_id"], "Deleted", "record", deleted_strategy, None, "human", "Cascade delete with coverage item")
                st.session_state[confirm_delete_key] = False
                save_state(ps)
                st.success("覆盖项已删除。")
                st.rerun()

st.markdown("### 全局覆盖项进度")
progress_rows = coverage_progress_by_suite(ps)
for row in progress_rows:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.1, 2, 1.2, 1.2])
        with c1:
            st.write(row["suite_id"])
        with c2:
            st.write(row["suite_name"])
        with c3:
            st.write(f"已分配覆盖项 {row['assigned_coverage_count']} 个")
        with c4:
            st.write(f"已确认 {row['confirmed_coverage_count']} 个")

eligible_req_ids = {req["req_id"] for _, req, _, _ in eligible_requirements}
coverage_by_req = {req_id: [item for item in ps["coverage_items"] if item.get("req_id") == req_id] for req_id in eligible_req_ids}
all_ready = all(items and all(item.get("review_status") == "Confirmed" for item in items) for items in coverage_by_req.values())

if st.button("完成覆盖项识别，进入套件详细设计", type="primary", use_container_width=True, disabled=not all_ready):
    st.session_state["active_suite_id"] = ps["test_suites"][0]["suite_id"] if ps.get("test_suites") else ""
    save_state(ps)
    switch_page_safe("pages/6_Suite_Detail_Design.py", "覆盖项识别已完成，请前往 Suite Detail Design 页面继续。")

if not all_ready:
    st.info("需要先为所有已纳入流程的需求生成并确认覆盖项，才能进入套件详细设计。")
