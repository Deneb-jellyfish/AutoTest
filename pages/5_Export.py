from __future__ import annotations

import streamlit as st

from services.export_service import export_excel, export_json
from utils.state_manager import requirements, test_cases


st.title("5) Export")
st.caption("Export structured artifacts to JSON or Excel for downstream test management tools.")

reqs = requirements()
cases = test_cases()

st.subheader("Download")
col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "Download JSON",
        data=export_json(reqs, cases),
        file_name="autotestdesign_artifacts.json",
        mime="application/json",
        disabled=not reqs,
    )
with col2:
    st.download_button(
        "Download Excel",
        data=export_excel(reqs, cases),
        file_name="autotestdesign_artifacts.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not reqs,
    )

st.subheader("Preview")
st.write("Requirements")
st.json(reqs[:2] if reqs else [])
st.write("Test cases")
st.json(cases[:2] if cases else [])

