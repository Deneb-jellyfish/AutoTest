from __future__ import annotations

import streamlit as st

from core.state_manager import get_state
from utils.export import export_project_excel, export_project_json, export_requirements_csv
from utils.ui import apply_reference_theme, render_hero, render_workflow_sidebar


apply_reference_theme()

with st.sidebar:
    render_workflow_sidebar("Persistence & Export")

render_hero(
    "Persistence & Export",
    "Export",
    "Download the current project state as JSON, Excel, or requirements CSV for downstream review and archival.",
)

ps = get_state()

col1, col2, col3 = st.columns(3)
with col1:
    st.download_button(
        "下载 JSON",
        data=export_project_json(ps),
        file_name="autotestdesign_project.json",
        mime="application/json",
    )
with col2:
    st.download_button(
        "下载 Requirements CSV",
        data=export_requirements_csv(ps),
        file_name="autotestdesign_requirements.csv",
        mime="text/csv",
    )
with col3:
    st.download_button(
        "下载 Excel",
        data=export_project_excel(ps),
        file_name="autotestdesign_project.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.subheader("导出预览")
st.write("project_meta")
st.json(ps["project_meta"])
st.write("requirements")
st.json(ps["requirements"][:2])
st.write("parsed_requirements")
st.json(ps["parsed_requirements"][:2])
