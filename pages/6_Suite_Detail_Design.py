from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from core.state_manager import find_strategy_by_cov, find_suite, get_state, save_state
from core.strategy_planner import sync_strategy_for_coverage
from core.test_suite_manager import (
    SUITE_TECHNIQUE_LABELS,
    TECHNIQUE_LABEL_TO_INTERNAL,
    TECHNIQUE_INTERNAL_TO_LABEL,
    ensure_default_test_suites,
    suite_counts,
    sync_coverage_suite_ids,
)
from utils.change_tracker import log_change
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


def switch_page_safe(target: str, fallback_message: str) -> None:
    if hasattr(st, "switch_page"):
        st.switch_page(target)
    else:
        st.success(fallback_message)


def build_suite_traceability_rows(ps: Dict[str, Any], suite_id: str, coverage_items: List[Dict[str, Any]], test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cases_by_cov: Dict[str, List[Dict[str, Any]]] = {}
    for test_case in test_cases:
        cases_by_cov.setdefault(test_case.get("coverage_id", ""), []).append(test_case)

    for coverage_item in coverage_items:
        linked_cases = cases_by_cov.get(coverage_item.get("cov_id", ""), [])
        if not linked_cases:
            rows.append(
                {
                    "suite_id": suite_id,
                    "coverage_id": coverage_item.get("cov_id", ""),
                    "coverage_title": coverage_item.get("title", ""),
                    "test_case_id": "",
                    "test_case_title": "",
                    "gap_note": "Missing test cases",
                }
            )
            continue

        for test_case in linked_cases:
            rows.append(
                {
                    "suite_id": suite_id,
                    "coverage_id": coverage_item.get("cov_id", ""),
                    "coverage_title": coverage_item.get("title", ""),
                    "test_case_id": test_case.get("test_case_id", ""),
                    "test_case_title": test_case.get("title", ""),
                    "gap_note": "",
                }
            )
    return rows


st.set_page_config(page_title="Suite Detail Design", layout="wide", page_icon=":bookmark_tabs:")
apply_reference_theme()

ps = get_state()
auto_changed = ensure_default_test_suites(ps)
auto_changed = sync_coverage_suite_ids(ps) or auto_changed
if auto_changed:
    save_state(ps)

with st.sidebar:
    render_workflow_sidebar("Suite Detail Design")

render_hero(
    "Suite-Focused Design",
    "Suite Detail Design",
    "Review each suite, confirm its coverage-to-technique mapping, then move into suite-scoped test case generation.",
)

if not ps.get("test_suites"):
    st.info("No test suites yet. Start from the Risk Assessment page to generate or design suites first.")
    st.stop()

active_suite_id = st.session_state.get("active_suite_id") or ps["test_suites"][0]["suite_id"]
if not find_suite(ps, active_suite_id):
    active_suite_id = ps["test_suites"][0]["suite_id"]
    st.session_state["active_suite_id"] = active_suite_id

left_col, right_col = st.columns([0.9, 1.4], gap="large")

with left_col:
    st.markdown("### Test Suites")
    for suite in ps.get("test_suites", []):
        counts = suite_counts(ps, suite["suite_id"])
        selected = suite["suite_id"] == active_suite_id
        with st.container(border=True):
            if st.button(
                f"{suite['suite_id']}  {suite['name']}",
                key=f"select_suite_{suite['suite_id']}",
                use_container_width=True,
                type="primary" if selected else "secondary",
            ):
                st.session_state["active_suite_id"] = suite["suite_id"]
                st.rerun()
            st.caption(f"[{suite.get('priority', 'Medium')}]")
            st.write(f"覆盖项 {counts['coverage_count']} 个 | 用例 {counts['test_case_count']} 个")

with right_col:
    suite = find_suite(ps, active_suite_id)
    if suite is None:
        st.info("Selected suite not found.")
        st.stop()

    suite_requirement_ids = suite.get("requirement_ids", [])
    suite_coverage_items = [item for item in ps.get("coverage_items", []) if active_suite_id in item.get("suite_ids", [])]
    suite_test_cases = [item for item in ps.get("test_cases", []) if active_suite_id in item.get("suite_ids", [])]

    st.markdown("### 套件信息")
    info1, info2 = st.columns(2)
    with info1:
        st.write(f"套件名称：{suite['suite_id']} {suite['name']}")
        st.write(f"优先级：{suite.get('priority', 'Medium')}")
    with info2:
        st.write("关联需求：", " ".join(suite_requirement_ids) or "None")
        st.write(
            "预选技术：",
            "  ".join(TECHNIQUE_INTERNAL_TO_LABEL.get(item, item) for item in suite.get("selected_techniques", [])) or "None",
        )

    st.markdown("### 覆盖项子集 + 策略确认")
    if not suite_coverage_items:
        st.info("当前套件还没有归属覆盖项。")
    else:
        table_rows = []
        for coverage_item in suite_coverage_items:
            strategy = find_strategy_by_cov(ps, coverage_item["cov_id"])
            table_rows.append(
                {
                    "coverage_id": coverage_item.get("cov_id", ""),
                    "title": coverage_item.get("title", ""),
                    "推荐技术": strategy.get("selected_technique", coverage_item.get("suggested_technique", "")) if strategy else coverage_item.get("suggested_technique", ""),
                    "状态": coverage_item.get("review_status", ""),
                }
            )
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        st.caption("如需调整覆盖项或技术映射，请前往 Coverage 页面修改；这里会自动同步最新结果。")

        if False:
            pass
            strategy = find_strategy_by_cov(ps, coverage_item["cov_id"])
            selected_technique = strategy.get("selected_technique", coverage_item.get("suggested_technique", "EP")) if strategy else coverage_item.get("suggested_technique", "EP")
            technique_label = TECHNIQUE_INTERNAL_TO_LABEL.get(selected_technique, selected_technique)

            with st.expander(f"{coverage_item['cov_id']} - {coverage_item.get('title', '')}", expanded=coverage_item.get("review_status") != "Confirmed"):
                col1, col2, col3 = st.columns([1.2, 1.1, 0.8])
                with col1:
                    technique_choice = st.selectbox(
                        "当前推荐技术",
                        options=SUITE_TECHNIQUE_LABELS,
                        index=SUITE_TECHNIQUE_LABELS.index(technique_label) if technique_label in SUITE_TECHNIQUE_LABELS else 0,
                        key=f"suite_cov_tech_{coverage_item['cov_id']}",
                    )
                with col2:
                    st.write(f"状态：{coverage_item.get('review_status', 'Draft')}")
                with col3:
                    confirm_clicked = st.button("确认", key=f"confirm_suite_cov_{coverage_item['cov_id']}", use_container_width=True)

                if confirm_clicked:
                    old_cov = deepcopy(coverage_item)
                    old_strategy = deepcopy(strategy) if strategy else None
                    coverage_item["review_status"] = "Confirmed"
                    coverage_item["last_edited_by"] = "human"
                    strategy_record = sync_strategy_for_coverage(
                        ps,
                        coverage_item,
                        TECHNIQUE_LABEL_TO_INTERNAL.get(technique_choice, "EP"),
                        strategy.get("technique_rationale", "") if strategy else "Confirmed from suite detail page",
                        strategy.get("generation_notes", "") if strategy else "",
                        review_status="Confirmed",
                    )
                    log_change(ps, "coverage_item", coverage_item["cov_id"], "Confirmed", "record", old_cov, coverage_item, "human", "Confirmed from suite detail design")
                    log_change(ps, "strategy_item", strategy_record["strategy_id"], "Confirmed", "record", old_strategy, strategy_record, "human", "Confirmed from suite detail design")
                    save_state(ps)
                    st.rerun()

    all_confirmed = bool(suite_coverage_items)
    if all_confirmed:
        if st.button("生成本套件的测试用例", type="primary", use_container_width=True):
            st.session_state["active_suite_id"] = active_suite_id
            st.session_state["auto_generate_suite_cases"] = active_suite_id
            switch_page_safe("pages/5_Test_Case_Workspace.py", "请前往 Test Case 页面，系统已聚焦当前套件。")

    st.markdown("### 可追溯性矩阵预览")
    if suite_test_cases:
        preview_rows = build_suite_traceability_rows(ps, active_suite_id, suite_coverage_items, suite_test_cases)
        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)
        if any(row.get("gap_note") for row in preview_rows):
            st.error("当前矩阵中仍有空列，需要补充覆盖项或测试用例。")
    else:
        st.info("当前套件还没有生成测试用例，生成后这里会展示追溯矩阵预览。")

    if st.button("补充覆盖项", type="secondary", use_container_width=True):
        st.session_state["active_suite_id"] = active_suite_id
        switch_page_safe("pages/4_Coverage_Planning.py", "请前往 Coverage & Strategy 页面为当前套件补充覆盖项。")
