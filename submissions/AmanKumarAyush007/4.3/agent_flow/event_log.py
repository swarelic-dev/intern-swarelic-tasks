"""Event audit helpers; storage backends may persist these events."""
from __future__ import annotations

import json
from typing import Any, Mapping


def serialize_event(event: Mapping[str, Any]) -> str:
    """Serialize an audit record as JSON for structured logging."""
    return json.dumps(dict(event), ensure_ascii=False, sort_keys=True, default=str)
