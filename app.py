import streamlit as st

from utils.state_manager import init_session_state


st.set_page_config(
    page_title="AutoTestDesign (Demo)",
    page_icon="🧪",
    layout="wide",
)

init_session_state()

st.title("AutoTestDesign (Demo)")
st.caption(
    "Requirements structuring → coverage identification → strategy selection → test case generation "
    "→ interactive review → export."
)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Requirements", len(st.session_state.requirements))
with col2:
    st.metric("Test Cases", len(st.session_state.test_cases))
with col3:
    st.metric("Modified Items", int(st.session_state.modified_count))

st.info(
    "Use the pages in the left sidebar to import requirements, review/edit results, generate test cases, and export artifacts.",
    icon="ℹ️",
)

