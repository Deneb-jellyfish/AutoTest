from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from core.exporter import export_to_csv_bundle, export_to_excel, export_to_json, load_project_from_json_bytes, save_export_file
from core.state_manager import get_state, save_state, set_state
from core.traceability import build_traceability_matrix
from utils.change_tracker import log_change
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


EXPORT_TEMP_UPLOAD = Path("exports/_uploaded_project_temp.json")


def _refresh_traceability(ps: dict) -> int:
    matrix = build_traceability_matrix(ps)
    ps["traceability_matrix"] = matrix
    return len(matrix)


def _traceability_csv_bytes(ps: dict) -> bytes:
    frame = pd.DataFrame(ps.get("traceability_matrix", []))
    return frame.to_csv(index=False).encode("utf-8-sig")


st.set_page_config(page_title="Optimization & Export", layout="wide", page_icon="🧪")
apply_reference_theme()

with st.sidebar:
    render_workflow_sidebar("Persistence & Export")

render_hero(
    "Optimization & Export",
    "Optimization and Export",
    "Refresh traceability, inspect export readiness, then write the full project state to JSON, CSV bundle, or Excel.",
)

ps = get_state()

metric1, metric2, metric3, metric4, metric5 = st.columns(5)
with metric1:
    st.metric("Requirements", len(ps.get("requirements", [])))
with metric2:
    st.metric("Strategies", len(ps.get("strategy_items", [])))
with metric3:
    st.metric("Suites", len(ps.get("test_suites", [])))
with metric4:
    st.metric("Test Cases", len(ps.get("test_cases", [])))
with metric5:
    st.metric("Traceability Rows", len(ps.get("traceability_matrix", [])))

action1, action2 = st.columns([1, 1])
with action1:
    if st.button("Build Traceability Matrix", type="primary", use_container_width=True):
        row_count = _refresh_traceability(ps)
        log_change(ps, "traceability_matrix", "traceability_matrix", "Regenerated", "record", None, {"row_count": row_count}, "system", "Rebuilt from export page")
        save_state(ps)
        st.success(f"已重建 traceability matrix，共 {row_count} 行。")
        st.rerun()
with action2:
    st.info("建议在正式导出前先重建一次 traceability matrix，确保 coverage、strategy 和 test case 的链路是最新的。")

st.markdown("### Export to Local Files")
export_col1, export_col2, export_col3 = st.columns(3)
with export_col1:
    if st.button("Export JSON", use_container_width=True, type="secondary"):
        path = save_export_file("project_state_export.json", export_to_json(ps))
        st.success(f"已写入 {path}")
with export_col2:
    if st.button("Export CSV Bundle", use_container_width=True, type="secondary"):
        path = save_export_file("project_state_export_csv_bundle.zip", export_to_csv_bundle(ps))
        st.success(f"已写入 {path}")
with export_col3:
    if st.button("Export Excel", use_container_width=True, type="secondary"):
        path = save_export_file("autotestdesign_export.xlsx", export_to_excel(ps))
        st.success(f"已写入 {path}")

st.markdown("### Download")
download_col1, download_col2, download_col3 = st.columns(3)
with download_col1:
    st.download_button(
        "Download JSON",
        data=export_to_json(ps),
        file_name="project_state_export.json",
        mime="application/json",
        use_container_width=True,
    )
with download_col2:
    st.download_button(
        "Download Traceability CSV",
        data=_traceability_csv_bytes(ps),
        file_name="traceability_matrix.csv",
        mime="text/csv",
        use_container_width=True,
    )
with download_col3:
    st.download_button(
        "Download Excel",
        data=export_to_excel(ps),
        file_name="autotestdesign_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.markdown("### Load Project from JSON Export")
uploaded_json = st.file_uploader("Upload exported JSON", type=["json"], key="export_json_loader")
if uploaded_json is not None:
    file_bytes = uploaded_json.getvalue()
    if st.button("Load Project from JSON Export", type="secondary"):
        try:
            EXPORT_TEMP_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
            EXPORT_TEMP_UPLOAD.write_bytes(file_bytes)
            loaded_state = load_project_from_json_bytes(file_bytes)
            set_state(loaded_state)
            st.success("已从 JSON 导出文件恢复项目状态。")
            st.rerun()
        except Exception as exc:
            st.error(f"加载 JSON 导出失败：{exc}")

st.markdown("### Export Preview")
preview_tab1, preview_tab2, preview_tab3, preview_tab4 = st.tabs(["Project", "Traceability", "Test Cases", "Change Log"])

with preview_tab1:
    st.json(
        {
            "project_info": ps.get("project_meta", {}),
            "requirements": ps.get("requirements", [])[:2],
            "structured_requirements": ps.get("parsed_requirements", [])[:2],
            "test_suites": ps.get("test_suites", [])[:2],
            "coverage_items": ps.get("coverage_items", [])[:2],
            "risk_items": ps.get("risk_items", [])[:2],
            "strategy_items": ps.get("strategy_items", [])[:2],
        }
    )

with preview_tab2:
    if ps.get("traceability_matrix"):
        st.dataframe(pd.DataFrame(ps["traceability_matrix"]), use_container_width=True, hide_index=True)
    else:
        st.info("当前还没有 traceability matrix。先点击 `Build Traceability Matrix`。")

with preview_tab3:
    if ps.get("test_cases"):
        st.dataframe(pd.DataFrame(ps["test_cases"]), use_container_width=True, hide_index=True)
    else:
        st.info("当前还没有 test cases。")

with preview_tab4:
    if ps.get("audit_log"):
        st.dataframe(pd.DataFrame(ps["audit_log"]), use_container_width=True, hide_index=True)
    else:
        st.info("当前还没有 change log。")
