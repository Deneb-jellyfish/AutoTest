from __future__ import annotations

import pandas as pd
import streamlit as st

from core.llm_client import LlmClient, load_config
from services.parser_service import split_requirements
from services.ingest_service import batch_parse_and_score, parse_and_score
from utils.state_manager import Keys, add_log


st.title("1) Requirement Import")
st.caption("Ingest requirements from CSV, plain text, or direct input.")

cfg = load_config()
llm = LlmClient(cfg)
st.sidebar.subheader("LLM Config")
st.sidebar.write(f"Base URL: `{cfg.base_url}`")
st.sidebar.write(f"Model: `{cfg.model or '(not set)'}`")
st.sidebar.write("API key: " + ("configured" if bool(cfg.api_key) else "missing"))
st.sidebar.write(f"Timeout: `{cfg.timeout_s:.0f}s`")
batch_size = int(st.sidebar.number_input("Batch size (requirements per call)", min_value=1, max_value=20, value=5, step=1))
if st.sidebar.button("Test LLM"):
    try:
        out = llm.chat(system="You are a helpful assistant.", user="Reply with OK only.", temperature=0)
        st.sidebar.success(f"LLM OK: {out[:50]}")
    except Exception as e:
        st.sidebar.error(f"LLM failed: {e}")
if not llm.enabled:
    st.error("LLM is not configured. Set OPENAI_API_KEY and OPENAI_MODEL (and optionally OPENAI_BASE_URL) in .env.", icon="🛑")
    st.stop()

tab1, tab2 = st.tabs(["CSV", "Plain Text"])

with tab1:
    st.subheader("Upload CSV")
    st.write("Expected columns: `id` (optional), `requirement`.")
    f = st.file_uploader("Choose a CSV file", type=["csv"])
    if f is not None:
        df = pd.read_csv(f)
        if "requirement" not in df.columns:
            st.error("CSV must include a `requirement` column.")
        else:
            st.dataframe(df.head(20), use_container_width=True)
            if st.button("Import from CSV", type="primary"):
                try:
                    with st.spinner("Calling LLM to parse and score requirements..."):
                        rows = []
                        for idx, row in df.iterrows():
                            rid = str(row.get("id") or f"REQ-{idx+1:03d}")
                            raw = str(row["requirement"])
                            rows.append({"id": rid, "text": raw})

                        reqs = []
                        total = len(rows)
                        progress = st.progress(0, text="Processing batches...")
                        for start in range(0, total, batch_size):
                            batch = rows[start : start + batch_size]
                            results = batch_parse_and_score(batch, llm)
                            # map back by id
                            by_id = {r.get("id"): r for r in results}
                            for item in batch:
                                rid = item["id"]
                                raw = item["text"]
                                r = by_id.get(rid)
                                if not isinstance(r, dict):
                                    # fallback single-call for the missing one
                                    single = parse_and_score(raw, llm)
                                    parsed, risk = single["parsed"], single["risk"]
                                else:
                                    parsed, risk = r.get("parsed") or {}, r.get("risk") or {}
                                reqs.append(
                                    {
                                        "id": rid,
                                        "raw_text": raw,
                                        "source": "csv",
                                        "parsed": parsed,
                                        "risk": risk,
                                        "coverage_items": [],
                                        "strategy": [],
                                        "modified_by_user": False,
                                    }
                                )
                            progress.progress(min(1.0, (start + len(batch)) / max(1, total)))
                    st.session_state[Keys.requirements] = reqs
                    add_log(f"Imported {len(reqs)} requirements from CSV.")
                    st.success(f"Imported {len(reqs)} requirements.")
                except Exception as e:
                    st.error(f"Import failed: {e}", icon="🛑")

with tab2:
    st.subheader("Paste Requirements")
    raw = st.text_area("Requirements text (one per paragraph)", height=240)
    if st.button("Import from text", type="primary"):
        try:
            parts = split_requirements(raw)
            if not parts:
                st.warning("No requirements detected. Add blank lines between requirements.")
                st.stop()
            with st.spinner("Calling LLM to parse and score requirements..."):
                rows = [{"id": f"REQ-{i:03d}", "text": t} for i, t in enumerate(parts, start=1)]
                reqs = []
                total = len(rows)
                progress = st.progress(0, text="Processing batches...")
                for start in range(0, total, batch_size):
                    batch = rows[start : start + batch_size]
                    results = batch_parse_and_score(batch, llm)
                    by_id = {r.get("id"): r for r in results}
                    for item in batch:
                        rid = item["id"]
                        t = item["text"]
                        r = by_id.get(rid)
                        if not isinstance(r, dict):
                            single = parse_and_score(t, llm)
                            parsed, risk = single["parsed"], single["risk"]
                        else:
                            parsed, risk = r.get("parsed") or {}, r.get("risk") or {}
                        reqs.append(
                            {
                                "id": rid,
                                "raw_text": t,
                                "source": "text",
                                "parsed": parsed,
                                "risk": risk,
                                "coverage_items": [],
                                "strategy": [],
                                "modified_by_user": False,
                            }
                        )
                    progress.progress(min(1.0, (start + len(batch)) / max(1, total)))
            st.session_state[Keys.requirements] = reqs
            add_log(f"Imported {len(reqs)} requirements from text.")
            st.success(f"Imported {len(reqs)} requirements.")
        except Exception as e:
            st.error(f"Import failed: {e}", icon="🛑")
