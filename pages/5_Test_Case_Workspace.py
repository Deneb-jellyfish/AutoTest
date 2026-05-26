from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from core.llm_client import LlmClient, load_config
from core.state_manager import find_requirement, find_suite, get_state, save_state
from core.test_case_generator import generate_test_cases_with_report
from core.test_suite_manager import ensure_default_test_suites, sync_coverage_suite_ids
from utils.change_tracker import log_change
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


EXECUTION_STATUS_OPTIONS = ["Not Run", "Passed", "Failed"]
PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}
PRIORITY_COLORS = {
    "High": ("#E2C2B7", "#7C4B3C"),
    "Medium": ("#DCCFB7", "#725A28"),
    "Low": ("#C8D8C8", "#48624B"),
}


def edit_list_block(values: List[str], key: str, label: str) -> List[str]:
    text_value = "\n".join(values or [])
    edited = st.text_area(label, value=text_value, height=110, key=key, placeholder="One item per line")
    return [line.strip() for line in edited.splitlines() if line.strip()]


def edit_test_data_block(values: Dict[str, Any], key: str) -> Dict[str, Any]:
    lines = [f"{field}={value}" for field, value in (values or {}).items()]
    edited = st.text_area("输入数据", value="\n".join(lines), height=130, key=key, placeholder="field=value")
    data: Dict[str, Any] = {}
    for line in edited.splitlines():
        if "=" not in line:
            continue
        field, value = line.split("=", 1)
        if field.strip():
            data[field.strip()] = value.strip()
    return data


def build_test_case_overview_rows(test_cases: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows = []
    for item in test_cases:
        rows.append(
            {
                "test_case_id": item.get("test_case_id", ""),
                "title": item.get("title", ""),
                "coverage_id": item.get("coverage_id", ""),
                "technique": item.get("technique", ""),
                "priority": item.get("priority", ""),
                "status": item.get("status", ""),
            }
        )
    return rows


def suite_priority_sort_key(suite: Dict[str, Any]) -> tuple[int, str]:
    return (PRIORITY_RANK.get(suite.get("priority", "Medium"), 99), suite.get("suite_id", ""))


def render_test_case_page_styles() -> None:
    st.markdown(
        """
        <style>
        .suite-priority-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 92px;
            padding: 8px 14px;
            border-radius: 999px;
            font-size: 0.92rem;
            font-weight: 700;
            letter-spacing: 0.01em;
        }
        .suite-code-chip {
            color: #2F3447;
            font-size: 0.98rem;
            font-weight: 700;
            text-align: center;
            margin-top: 8px;
            margin-bottom: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_priority_badge(priority: str) -> str:
    background, text = PRIORITY_COLORS.get(priority, PRIORITY_COLORS["Medium"])
    return (
        f"<span class='suite-priority-badge' style='background:{background};color:{text};'>"
        f"{escape(priority)}</span>"
    )


def generate_cases_for_suite(ps: Dict[str, Any], suite: Dict[str, Any], use_llm: bool, llm_client: LlmClient) -> Dict[str, Any]:
    generated_total = 0
    preserved_total = 0
    replaced_total = 0
    warnings: List[str] = []

    suite_coverage = [item for item in ps.get("coverage_items", []) if suite["suite_id"] in item.get("suite_ids", [])]
    coverage_ids_by_req: Dict[str, List[str]] = {}
    for coverage_item in suite_coverage:
        coverage_ids_by_req.setdefault(coverage_item.get("req_id", ""), []).append(coverage_item["cov_id"])

    for req_id, target_coverage_ids in coverage_ids_by_req.items():
        requirement = find_requirement(ps, req_id)
        if requirement is None:
            continue
        result = generate_test_cases_with_report(
            ps=ps,
            requirement=requirement,
            target_coverage_ids=target_coverage_ids,
            preserve_approved=True,
            use_llm=use_llm,
            llm_client=llm_client,
        )
        for case in result["test_cases"]:
            log_change(
                ps,
                "test_case",
                case["test_case_id"],
                "Created",
                "record",
                None,
                case,
                case.get("last_edited_by", "rule"),
                f"Generated from suite {suite['suite_id']}",
            )
        generated_total += result["generated_count"]
        preserved_total += result["preserved_count"]
        replaced_total += result["replaced_count"]
        warnings.extend(result["warnings"])

    coverage_ids = {item["cov_id"] for item in suite_coverage}
    for test_case in ps.get("test_cases", []):
        if test_case.get("coverage_id") in coverage_ids and suite["suite_id"] not in test_case.get("suite_ids", []):
            test_case.setdefault("suite_ids", []).append(suite["suite_id"])

    return {
        "generated_total": generated_total,
        "preserved_total": preserved_total,
        "replaced_total": replaced_total,
        "warnings": warnings,
    }


def generate_cases_for_suites(
    ps: Dict[str, Any],
    suites: List[Dict[str, Any]],
    use_llm: bool,
    llm_client: LlmClient,
    update_existing: bool,
) -> Dict[str, Any]:
    generated_total = 0
    preserved_total = 0
    replaced_total = 0
    processed_suites = 0
    warnings: List[str] = []

    for suite in suites:
        has_existing_cases = any(suite["suite_id"] in item.get("suite_ids", []) for item in ps.get("test_cases", []))
        if not update_existing and has_existing_cases:
            continue
        result = generate_cases_for_suite(ps, suite, use_llm, llm_client)
        generated_total += result["generated_total"]
        preserved_total += result["preserved_total"]
        replaced_total += result["replaced_total"]
        warnings.extend([f"{suite['suite_id']}: {warning}" for warning in result["warnings"]])
        processed_suites += 1

    return {
        "processed_suites": processed_suites,
        "generated_total": generated_total,
        "preserved_total": preserved_total,
        "replaced_total": replaced_total,
        "warnings": warnings,
    }


def report_generation_result(message: str, result: Dict[str, Any]) -> None:
    for warning in result["warnings"]:
        st.warning(warning)
    st.success(message)


st.set_page_config(page_title="Test Cases", layout="wide", page_icon=":card_file_box:")
apply_reference_theme()
render_test_case_page_styles()

ps = get_state()
use_llm = bool(st.session_state.get("use_llm", False))
llm_client = LlmClient(load_config())

auto_changed = ensure_default_test_suites(ps)
auto_changed = sync_coverage_suite_ids(ps) or auto_changed
if auto_changed:
    save_state(ps)

with st.sidebar:
    render_workflow_sidebar("Test Cases")

render_hero(
    "Suite-Based Test Cases",
    "Test Case Workspace",
    "Prioritize suites, generate cases in batch, and update suite cases when new coverage items arrive.",
)

if not ps.get("test_suites"):
    st.info("No suites yet. Design suites first from Risk Assessment.")
    st.stop()

priority_sorted_suites = sorted(ps["test_suites"], key=suite_priority_sort_key)
active_suite_id = st.session_state.get("active_suite_id") or priority_sorted_suites[0]["suite_id"]
active_suite = find_suite(ps, active_suite_id) or priority_sorted_suites[0]
st.session_state["active_suite_id"] = active_suite["suite_id"]

auto_generate_suite_id = st.session_state.pop("auto_generate_suite_cases", None)
if auto_generate_suite_id:
    suite = find_suite(ps, auto_generate_suite_id)
    if suite is not None:
        result = generate_cases_for_suite(ps, suite, use_llm, llm_client)
        save_state(ps)
        report_generation_result(
            f"{suite['suite_id']} generated {result['generated_total']} cases, preserved {result['preserved_total']} approved cases, replaced {result['replaced_total']} older drafts.",
            result,
        )

global_action_1, global_action_2 = st.columns(2)
with global_action_1:
    if st.button("生成所有套件测试用例", type="primary", use_container_width=True):
        result = generate_cases_for_suites(ps, priority_sorted_suites, use_llm, llm_client, update_existing=False)
        save_state(ps)
        report_generation_result(
            f"已处理 {result['processed_suites']} 个套件，新增 {result['generated_total']} 条用例，保留 {result['preserved_total']} 条已批准用例。",
            result,
        )
        st.rerun()
with global_action_2:
    if st.button("更新所有套件测试用例", type="secondary", use_container_width=True):
        result = generate_cases_for_suites(ps, priority_sorted_suites, use_llm, llm_client, update_existing=True)
        save_state(ps)
        report_generation_result(
            f"已更新 {result['processed_suites']} 个套件，新增 {result['generated_total']} 条用例，替换 {result['replaced_total']} 条旧草稿。",
            result,
        )
        st.rerun()

st.markdown("### Suite Priority Queue")
queue_cols = st.columns(len(priority_sorted_suites))
for col, suite in zip(queue_cols, priority_sorted_suites):
    with col:
        st.markdown(render_priority_badge(suite.get("priority", "Medium")), unsafe_allow_html=True)
        st.markdown(f"<div class='suite-code-chip'>{escape(suite['suite_id'])}</div>", unsafe_allow_html=True)
        button_label = "当前" if suite["suite_id"] == active_suite["suite_id"] else "选择"
        if st.button(button_label, key=f"focus_suite_{suite['suite_id']}", use_container_width=True):
            st.session_state["active_suite_id"] = suite["suite_id"]
            st.rerun()

active_suite = find_suite(ps, st.session_state["active_suite_id"]) or priority_sorted_suites[0]
suite_coverage = [item for item in ps.get("coverage_items", []) if active_suite["suite_id"] in item.get("suite_ids", [])]
suite_test_cases = [item for item in ps.get("test_cases", []) if active_suite["suite_id"] in item.get("suite_ids", [])]

status_counts = {
    "Passed": len([item for item in suite_test_cases if item.get("status") == "Passed"]),
    "Failed": len([item for item in suite_test_cases if item.get("status") == "Failed"]),
    "Not Run": len([item for item in suite_test_cases if item.get("status", "Not Run") == "Not Run"]),
}

title_left, title_right = st.columns([3.2, 1])
with title_left:
    st.markdown(f"### 套件：{active_suite['suite_id']} {active_suite['name']}")
with title_right:
    st.markdown(render_priority_badge(active_suite.get("priority", "Medium")), unsafe_allow_html=True)

metric1, metric2, metric3, metric4 = st.columns(4)
with metric1:
    st.metric("总用例数", len(suite_test_cases))
with metric2:
    st.metric("通过", status_counts["Passed"])
with metric3:
    st.metric("失败", status_counts["Failed"])
with metric4:
    st.metric("未执行", status_counts["Not Run"])

current_action_1, current_action_2, current_action_3 = st.columns([1.2, 1.2, 1])
with current_action_1:
    if st.button(f"生成 {active_suite['suite_id']} 的测试用例", type="primary", use_container_width=True, disabled=bool(suite_test_cases)):
        result = generate_cases_for_suite(ps, active_suite, use_llm, llm_client)
        save_state(ps)
        report_generation_result(
            f"{active_suite['suite_id']} generated {result['generated_total']} cases, preserved {result['preserved_total']} approved cases, replaced {result['replaced_total']} older drafts.",
            result,
        )
        st.rerun()
with current_action_2:
    if st.button(f"更新 {active_suite['suite_id']} 的测试用例", type="secondary", use_container_width=True, disabled=not bool(suite_coverage)):
        result = generate_cases_for_suite(ps, active_suite, use_llm, llm_client)
        save_state(ps)
        report_generation_result(
            f"{active_suite['suite_id']} updated with {result['generated_total']} new cases and {result['replaced_total']} refreshed drafts.",
            result,
        )
        st.rerun()
with current_action_3:
    st.caption(f"覆盖项 {len(suite_coverage)} 个 | 套件优先级 {active_suite.get('priority', 'Medium')}")

if suite_test_cases:
    st.dataframe(pd.DataFrame(build_test_case_overview_rows(suite_test_cases)), use_container_width=True, hide_index=True)
else:
    st.info("当前套件还没有测试用例。")

sorted_cases = sorted(
    suite_test_cases,
    key=lambda item: (
        item.get("coverage_id", ""),
        item.get("test_case_id", ""),
    ),
)

for item in sorted_cases:
    requirement = find_requirement(ps, item.get("requirement_id", ""))
    with st.expander(f"{item['test_case_id']} - {item.get('title', '')}", expanded=False):
        st.write(f"关联需求：{item.get('requirement_id', '')}")
        st.write(f"关联覆盖项：{item.get('coverage_id', '')}")
        st.write(f"使用技术：{item.get('technique', '')}")

        title = st.text_input("标题", value=item.get("title", ""), key=f"tc_title_{item['test_case_id']}")
        objective = st.text_area("目标", value=item.get("objective", ""), height=90, key=f"tc_objective_{item['test_case_id']}")
        test_data = edit_test_data_block(item.get("test_data", {}), key=f"tc_data_{item['test_case_id']}")
        expected_result = edit_list_block(item.get("expected_result", []), key=f"tc_expected_{item['test_case_id']}", label="期望结果")
        preconditions = edit_list_block(item.get("preconditions", []), key=f"tc_pre_{item['test_case_id']}", label="前置条件")
        steps = edit_list_block(item.get("steps", []), key=f"tc_steps_{item['test_case_id']}", label="步骤")
        status = st.selectbox(
            "执行状态",
            EXECUTION_STATUS_OPTIONS,
            index=EXECUTION_STATUS_OPTIONS.index(item.get("status", "Not Run")) if item.get("status", "Not Run") in EXECUTION_STATUS_OPTIONS else 0,
            key=f"tc_status_{item['test_case_id']}",
        )
        notes = st.text_area("备注", value=item.get("notes", ""), height=80, key=f"tc_notes_{item['test_case_id']}")

        btn1, btn2 = st.columns(2)
        save_clicked = btn1.button("保存", key=f"save_tc_{item['test_case_id']}", type="primary", use_container_width=True)
        delete_clicked = btn2.button("删除", key=f"delete_tc_{item['test_case_id']}", type="secondary", use_container_width=True)

        if save_clicked:
            old_value = deepcopy(item)
            item["title"] = title.strip()
            item["objective"] = objective.strip()
            item["test_data"] = test_data
            item["expected_result"] = expected_result
            item["preconditions"] = preconditions
            item["steps"] = steps
            item["status"] = status
            item["notes"] = notes.strip()
            item["last_edited_by"] = "human"
            if requirement:
                item["requirement_id"] = requirement["req_id"]
            log_change(ps, "test_case", item["test_case_id"], "Edited", "record", old_value, item, "human", "Edited from suite test case page")
            save_state(ps)
            st.success(f"{item['test_case_id']} 已保存。")
            st.rerun()

        if delete_clicked:
            old_value = deepcopy(item)
            ps["test_cases"] = [row for row in ps.get("test_cases", []) if row.get("test_case_id") != item["test_case_id"]]
            log_change(ps, "test_case", item["test_case_id"], "Deleted", "record", old_value, None, "human", "Deleted from suite test case page")
            save_state(ps)
            st.success("测试用例已删除。")
            st.rerun()
