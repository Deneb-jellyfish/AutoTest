from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from core.data_model import utc_now_iso


DB_PATH = Path("db/app_state.db")


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_state (
            id INTEGER PRIMARY KEY,
            data TEXT,
            saved_at TEXT
        )
        """
    )
    return conn


def save_to_db(project_state: Dict[str, Any]) -> None:
    conn = _get_connection()
    conn.execute("DELETE FROM project_state")
    conn.execute(
        "INSERT INTO project_state (data, saved_at) VALUES (?, ?)",
        (json.dumps(project_state, ensure_ascii=False), utc_now_iso()),
    )
    conn.commit()
    conn.close()


def load_from_db() -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    row = conn.execute("SELECT data FROM project_state ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None
