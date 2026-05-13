from __future__ import annotations

import streamlit as st

from components.editable_table import editable_list
from components.highlight_renderer import render_highlighted
from utils.state_manager import Keys, bump_modified, requirements


st.title("2) Structured Review")
st.caption("Interactive review: edit parsed fields and keep evidence of human validation.")

reqs = requirements()
if not reqs:
    st.warning("No requirements yet. Go to 'Requirement Import' first.")
    st.stop()

req_id = st.selectbox("Select requirement", [r["id"] for r in reqs])
req = next(r for r in reqs if r["id"] == req_id)

st.subheader("Raw Requirement")
st.write(req["raw_text"])

st.subheader("Highlighted View")
html = render_highlighted(req["raw_text"], req.get("parsed", {}))
st.markdown(html, unsafe_allow_html=True)

st.subheader("Edit Parsed Components")
col1, col2 = st.columns(2)
with col1:
    input_fields = editable_list("input_fields", req["parsed"].get("input_fields", []) or [])
    data_ranges = editable_list("data_ranges", req["parsed"].get("data_ranges", []) or [])
with col2:
    conditions = editable_list("conditions", req["parsed"].get("conditions", []) or [])
    expected_actions = editable_list("expected_actions", req["parsed"].get("expected_actions", []) or [])

if st.button("Apply changes", type="primary"):
    req["parsed"]["input_fields"] = input_fields
    req["parsed"]["data_ranges"] = data_ranges
    req["parsed"]["conditions"] = conditions
    req["parsed"]["expected_actions"] = expected_actions
    if not req.get("modified_by_user", False):
        req["modified_by_user"] = True
        bump_modified(1)
    st.success("Updated parsed content.")

st.divider()
st.subheader("Current Parsed JSON")
st.json(req["parsed"])

