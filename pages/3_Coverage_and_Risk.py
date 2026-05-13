from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from components.editable_table import editable_list
from components.risk_badge import risk_badge
from utils.state_manager import bump_modified, requirements


def suggest_coverage_items(parsed: Dict[str, Any]) -> List[str]:
    items: List[str] = []
    for f in parsed.get("input_fields", []) or []:
        items.append(f"EP partitions for {f} (valid/invalid)")
    for r in parsed.get("data_ranges", []) or []:
        items.append(f"BVA boundaries for {r}")
    for c in parsed.get("conditions", []) or []:
        items.append(f"Condition branch: {c[:80]}")
    return items[:30]


def suggest_strategy(parsed: Dict[str, Any]) -> List[str]:
    strat: List[str] = ["EP"]
    if parsed.get("data_ranges"):
        strat.append("BVA")
    if parsed.get("conditions") and len(parsed.get("conditions") or []) >= 2:
        strat.append("DT")
    return strat


st.title("3) Coverage and Risk Review")
st.caption("Review risk score/priority and define coverage items + strategy.")

reqs = requirements()
if not reqs:
    st.warning("No requirements yet. Go to 'Requirement Import' first.")
    st.stop()

req_id = st.selectbox("Select requirement", [r["id"] for r in reqs])
req = next(r for r in reqs if r["id"] == req_id)

st.subheader("Risk")
col1, col2 = st.columns([1, 2])
with col1:
    risk_badge(req.get("risk", {}).get("level", "Medium"))
with col2:
    st.json(req.get("risk", {}))

st.subheader("Coverage Items (Editable)")
if not req.get("coverage_items"):
    req["coverage_items"] = suggest_coverage_items(req.get("parsed", {}))
coverage_items = editable_list("coverage_items", req.get("coverage_items", []) or [])

st.subheader("Coverage Strategy (Editable)")
if not req.get("strategy"):
    req["strategy"] = suggest_strategy(req.get("parsed", {}))
strategy = editable_list("strategy", req.get("strategy", []) or [])

if st.button("Apply coverage changes", type="primary"):
    req["coverage_items"] = coverage_items
    req["strategy"] = strategy
    if not req.get("modified_by_user", False):
        req["modified_by_user"] = True
        bump_modified(1)
    st.success("Updated coverage items and strategy.")

