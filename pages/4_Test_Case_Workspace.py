from __future__ import annotations

import pandas as pd
import streamlit as st

from core.llm_client import LlmClient, load_config
from services.testgen_service import batch_generate_test_cases
from utils.state_manager import Keys, bump_modified, requirements, test_cases


st.title("4) Test Case Workspace")
st.caption("Generate and interactively refine black-box test cases with traceability.")

reqs = requirements()
if not reqs:
    st.warning("No requirements yet. Go to 'Requirement Import' first.")
    st.stop()

cfg = load_config()
llm = LlmClient(cfg)
if not llm.enabled:
    st.error("LLM is not configured. Set OPENAI_API_KEY and OPENAI_MODEL in .env.", icon="🛑")
    st.stop()

batch_size = int(st.sidebar.number_input("Batch size (requirements per call)", min_value=1, max_value=20, value=5, step=1))
col1, col2 = st.columns([1, 2])
with col1:
    if st.button("Generate test cases", type="primary"):
        try:
            with st.spinner("Calling LLM to generate test cases..."):
                cases = batch_generate_test_cases(reqs, llm, batch_size=batch_size)
            st.session_state[Keys.test_cases] = cases
            st.success(f"Generated {len(cases)} test cases.")
        except Exception as e:
            st.error(f"Generation failed: {e}", icon="🛑")
with col2:
    st.write("Tip: edit cells directly; changes are tracked as `user_modified=True` and version increments.")

cases = test_cases()
if not cases:
    st.info("No test cases yet. Click 'Generate test cases'.")
    st.stop()

opt_col1, opt_col2 = st.columns([1, 3])
with opt_col1:
    if st.button("Optimize (deduplicate)"):
        seen = set()
        optimized = []
        for tc in cases:
            key = (
                str(tc.get("req_id", "")),
                str(tc.get("technique", "")),
                str(tc.get("coverage_item", "")),
                str(tc.get("condition", "")),
                str(tc.get("input_data", "")),
                str(tc.get("expected", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            optimized.append(tc)
        st.session_state[Keys.test_cases] = optimized
        st.success(f"Optimized: {len(cases)} → {len(optimized)} (duplicates removed).")
        cases = optimized
with opt_col2:
    st.caption("Optimization removes exact duplicates to improve coverage efficiency (extra credit: FR 7.0).")

df = pd.DataFrame(cases)
edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="tc_editor")

if st.button("Apply test case edits"):
    new_cases = edited.to_dict(orient="records")
    changed = 0
    for old, new in zip(cases, new_cases):
        if old != new:
            new["user_modified"] = True
            new["ai_generated"] = bool(old.get("ai_generated", True))
            new["version"] = int(old.get("version", 1)) + 1
            changed += 1
    st.session_state[Keys.test_cases] = new_cases
    if changed:
        bump_modified(changed)
    st.success(f"Applied edits. Modified rows: {changed}.")
