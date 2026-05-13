from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import streamlit as st


@dataclass(frozen=True)
class Keys:
    requirements: str = "requirements"
    test_cases: str = "test_cases"
    modified_count: str = "modified_count"
    run_log: str = "run_log"


def init_session_state() -> None:
    if Keys.requirements not in st.session_state:
        st.session_state[Keys.requirements] = []
    if Keys.test_cases not in st.session_state:
        st.session_state[Keys.test_cases] = []
    if Keys.modified_count not in st.session_state:
        st.session_state[Keys.modified_count] = 0
    if Keys.run_log not in st.session_state:
        st.session_state[Keys.run_log] = []


def bump_modified(delta: int = 1) -> None:
    st.session_state[Keys.modified_count] = int(st.session_state.get(Keys.modified_count, 0)) + int(delta)


def add_log(message: str) -> None:
    st.session_state[Keys.run_log].append(message)


def requirements() -> List[Dict[str, Any]]:
    return st.session_state[Keys.requirements]


def test_cases() -> List[Dict[str, Any]]:
    return st.session_state[Keys.test_cases]

