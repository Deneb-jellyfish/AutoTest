from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st


def editable_list(label: str, values: List[str]) -> List[str]:
    df = pd.DataFrame({"value": values})
    edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key=f"ed_{label}")
    out = [str(v).strip() for v in edited["value"].tolist() if str(v).strip()]
    return out

