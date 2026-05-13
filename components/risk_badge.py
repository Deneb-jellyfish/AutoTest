from __future__ import annotations

import streamlit as st


def risk_badge(level: str) -> None:
    level = (level or "Medium").capitalize()
    if level == "High":
        st.error("High", icon="⚠️")
    elif level == "Low":
        st.success("Low", icon="✅")
    else:
        st.warning("Medium", icon="🟡")

