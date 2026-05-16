from __future__ import annotations

import json
from typing import Any, Dict

from core.data_model import utc_now_iso


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def log_change(
    ps: Dict[str, Any],
    object_type: str,
    object_id: str,
    action: str,
    field_name: str,
    old_value: Any,
    new_value: Any,
    changed_by: str,
    reason: str,
) -> Dict[str, Any]:
    entry = {
        "log_id": f"LOG-{len(ps['audit_log']) + 1:03d}",
        "timestamp": utc_now_iso(),
        "object_type": object_type,
        "object_id": object_id,
        "action": action,
        "changed_field": field_name,
        "old_value": _stringify(old_value),
        "new_value": _stringify(new_value),
        "changed_by": changed_by,
        "reason": reason,
    }
    ps["audit_log"].append(entry)
    return entry
