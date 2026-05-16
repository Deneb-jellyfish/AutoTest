from __future__ import annotations

from typing import Iterable, Sequence, Tuple

import streamlit as st


THEME_CSS = """
<style>
    .stApp {
        background: linear-gradient(180deg, #fff9ec 0%, #fffdf8 100%);
        color: #2d2a26;
    }
    [data-testid="stSidebar"] {
        background:
            linear-gradient(rgba(247, 209, 114, 0.18) 1px, transparent 1px),
            linear-gradient(90deg, rgba(247, 209, 114, 0.18) 1px, transparent 1px),
            linear-gradient(180deg, #fff0c9 0%, #fff7df 100%);
        background-size: 28px 28px, 28px 28px, auto;
        border-right: 1px solid rgba(168, 102, 31, 0.12);
    }
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 1180px;
    }
    .ref-hero {
        background: rgba(255,255,255,0.88);
        border: 1px solid rgba(168, 102, 31, 0.16);
        border-radius: 28px;
        padding: 1.6rem 1.8rem 1.8rem 1.8rem;
        box-shadow: 0 18px 40px rgba(164, 111, 24, 0.08);
        margin-bottom: 1.25rem;
    }
    .ref-kicker {
        color: #f59e0b;
        letter-spacing: 0.12em;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
    }
    .ref-title {
        font-size: 3.1rem;
        line-height: 1.05;
        font-weight: 800;
        margin: 0 0 0.8rem 0;
        color: #1f1f1f;
    }
    .ref-subtitle {
        font-size: 1.18rem;
        color: #6b6b6b;
        margin: 0;
    }
    .ref-card-title {
        font-size: 1.65rem;
        font-weight: 800;
        margin: 0 0 0.35rem 0;
        color: #262626;
    }
    .ref-card-desc {
        color: #7a746b;
        margin: 0 0 0.9rem 0;
        font-size: 0.98rem;
    }
    .ref-section {
        background: rgba(255,255,255,0.78);
        border: 1px solid rgba(168, 102, 31, 0.16);
        border-radius: 24px;
        padding: 1.2rem 1.25rem 1.15rem 1.25rem;
        box-shadow: 0 10px 24px rgba(164, 111, 24, 0.05);
        margin-bottom: 1rem;
    }
    .ref-mini {
        background: rgba(255,255,255,0.84);
        border: 1px solid rgba(249, 199, 79, 0.28);
        border-radius: 18px;
        padding: 1rem 1.05rem;
        box-shadow: 0 8px 16px rgba(164, 111, 24, 0.04);
    }
    .ref-note {
        padding: 0.85rem 1rem;
        border-radius: 16px;
        background: #fff6df;
        border: 1px solid rgba(245, 158, 11, 0.18);
        color: #855314;
    }
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.82);
        border: 1px solid rgba(249, 199, 79, 0.28);
        padding: 1rem 1.05rem;
        border-radius: 18px;
        box-shadow: 0 8px 16px rgba(164, 111, 24, 0.04);
    }
    div[data-testid="stMetric"] label {
        color: #7a746b !important;
    }
    div[data-testid="stExpander"] {
        border: 1px solid rgba(168, 102, 31, 0.14);
        border-radius: 24px;
        background: rgba(255,255,255,0.82);
        overflow: hidden;
        box-shadow: 0 10px 24px rgba(164, 111, 24, 0.05);
        margin-bottom: 1rem;
    }
    div[data-testid="stExpander"] summary {
        font-size: 1.1rem;
        font-weight: 700;
        color: #2d2a26;
    }
    .stButton > button, .stDownloadButton > button {
        border-radius: 16px;
        padding: 0.65rem 1rem;
        border: 1px solid rgba(168, 102, 31, 0.15);
        box-shadow: none;
    }
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
        background: linear-gradient(180deg, #f7d58f 0%, #efc46f 100%);
        color: #53381b;
        border: 1px solid rgba(168, 102, 31, 0.18);
    }
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
        background: linear-gradient(180deg, #f5ce7d 0%, #e9bc5f 100%);
        color: #452c13;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.88);
        color: #5f5242;
    }
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
        border-radius: 20px;
        overflow: hidden;
        border: 1px solid rgba(168, 102, 31, 0.12);
        background: rgba(255,255,255,0.9);
    }
    div[data-testid="stAlert"] {
        border-radius: 18px;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"], .stFileUploader {
        border-radius: 16px !important;
    }
</style>
"""


def apply_reference_theme() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_workflow_sidebar(current_label: str) -> None:
    items = [
        ("Requirement Import", "pages/1_Requirement_Import.py"),
        ("Structuring & Review", "pages/2_Structured_Requirement_Review.py"),
        ("Risk Assessment", "pages/3_Risk_Assessment.py"),
        ("Coverage & Strategy", "pages/4_Coverage_Planning.py"),
        ("Persistence & Export", "pages/5_Export.py"),
    ]
    st.markdown("### AutoTestDesign Workflow")
    for label, target in items:
        try:
            st.page_link(target, label=label, icon="🟠" if label == current_label else "⚪")
        except Exception:
            st.write(f"{'●' if label == current_label else '○'} {label}")


def render_hero(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="ref-hero">
            <div class="ref-kicker">{kicker}</div>
            <div class="ref-title">{title}</div>
            <p class="ref-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, description: str = "") -> None:
    st.markdown(
        f"""
        <div class="ref-section">
            <div class="ref-card-title">{title}</div>
            <p class="ref-card-desc">{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
