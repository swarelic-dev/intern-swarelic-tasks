"""Strict JSON decoding and validation for call-routing rules."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine import Action, Condition, Rule

_ACTIONS = frozenset({"route", "voicemail", "escalate", "hangup", "play_message"})
_OPERATORS = frozenset({"eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains", "startswith"})


def load_rules_from_json(path: str | Path) -> list[Rule]:
    """Read UTF-8 JSON from disk; raise FileNotFoundError or ValueError on failure."""
    location = Path(path)
    if not location.is_file():
        raise FileNotFoundError(f"Rule file not found: {location}")
    try:
        with location.open(encoding="utf-8") as stream:
            document = json.load(stream)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"Malformed JSON in {location}") from exc
    return load_rules_from_dict(document)


def load_rules_from_dict(data: list[dict[str, Any]]) -> list[Rule]:
    """Validate an already-decoded document and return strongly typed rules."""
    if not isinstance(data, list):
        raise ValueError("Rules document must be a list")
    result: list[Rule] = []
    seen: set[str] = set()
    for index, item in enumerate(data):
        location = f"rule[{index}]"
        if not isinstance(item, dict) or not {"id", "name", "priority", "conditions", "action"} <= item.keys():
            raise ValueError(f"{location}: required fields are missing")
        identifier, name, priority = item["id"], item["name"], item["priority"]
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise ValueError(f"{location}: id must be unique and nonempty")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{location}: name must be nonempty")
        if type(priority) is not int:
            raise ValueError(f"{location}: priority must be an integer")
        if not isinstance(item["conditions"], list):
            raise ValueError(f"{location}: conditions must be a list")
        conditions: list[Condition] = []
        for number, condition in enumerate(item["conditions"]):
            where = f"{location}.conditions[{number}]"
            if not isinstance(condition, dict) or not {"field", "operator", "value"} <= condition.keys():
                raise ValueError(f"{where}: missing condition field")
            if not isinstance(condition["field"], str) or not condition["field"].strip():
                raise ValueError(f"{where}: field must be nonempty")
            if condition["operator"] not in _OPERATORS:
                raise ValueError(f"{where}: unsupported operator")
            if condition["operator"] in ("in", "not_in") and not isinstance(condition["value"], list):
                raise ValueError(f"{where}: membership comparison requires a list")
            conditions.append(Condition(condition["field"], condition["operator"], condition["value"]))
        action = item["action"]
        if not isinstance(action, dict) or action.get("type") not in _ACTIONS:
            raise ValueError(f"{location}: unsupported or missing action type")
        seen.add(identifier)
        result.append(Rule(identifier, name, priority, conditions,
                           Action(action["type"], {k: v for k, v in action.items() if k != "type"})))
    return result
