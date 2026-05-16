from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from core.state_manager import get_state, reset_state, save_state, set_state
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


st.set_page_config(page_title="AutoTestDesign", layout="wide", page_icon="🧪")
apply_reference_theme()

ps = get_state()

with st.sidebar:
    render_workflow_sidebar("")
    st.divider()

    st.subheader("⚙️ 配置")
    use_llm = st.toggle(
        "启用真实 LLM",
        value=bool(st.session_state.get("use_llm", False)),
        help="关闭时使用规则引擎，开启时调用已配置的 LLM。",
    )
    st.session_state["use_llm"] = use_llm

    if use_llm:
        st.success("✅ LLM 已启用")
    else:
        st.warning("⚠️ 使用规则引擎（Mock 模式）")

    st.divider()

    st.subheader("📁 项目控制")
    if st.button("💾 保存项目", use_container_width=True):
        save_state(ps)
        st.success("已保存到 SQLite")

    if st.button("🔄 加载示例项目", use_container_width=True):
        sample_path = Path("data/sample_project.json")
        with sample_path.open("r", encoding="utf-8") as handle:
            sample = json.load(handle)
        set_state(sample)
        st.success("示例项目已加载")
        st.rerun()

    if st.button("🗑️ 重置项目", use_container_width=True, type="secondary"):
        if st.session_state.get("confirm_reset"):
            reset_state()
            st.session_state["confirm_reset"] = False
            st.success("项目已重置")
            st.rerun()
        else:
            st.session_state["confirm_reset"] = True
            st.warning("再次点击确认重置")

    st.divider()
    st.caption("默认保存路径：db/app_state.db")

render_hero(
    "AI-Assisted Test Design",
    "AutoTestDesign Workflow",
    "A calm workspace for requirement analysis, risk-based prioritization, coverage review, and traceable test design.",
)

meta = ps["project_meta"]
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("需求数", len(ps["requirements"]))
with col2:
    st.metric("结构化结果", len(ps["parsed_requirements"]))
with col3:
    st.metric("风险项", len(ps["risk_items"]))
with col4:
    st.metric("覆盖项", len(ps["coverage_items"]))

st.info(
    f"当前项目：`{meta['project_name']}` | 目标应用：`{meta['target_app']}` | "
    f"最后修改：`{meta['last_modified']}`"
)

st.markdown(
    """
    当前主流程已经按新的批量导入与批量结构化逻辑调整：

    - `1_Requirement_Import`
    - `2_Structured_Requirement_Review`
    - `3_Risk_Assessment`
    - `4_Coverage_Planning`
    - `5_Export`
    """
)
