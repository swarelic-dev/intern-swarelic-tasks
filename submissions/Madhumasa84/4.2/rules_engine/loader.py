"""
rules_engine/loader.py — Rules Loader for Exercise 4.2
"""
import json
from pathlib import Path
from .engine import Rule, Condition, Action, VALID_ACTION_TYPES


def load_rules_from_json(path: str | Path) -> list[Rule]:
    """
    Load rules from a JSON file.

    Validates:
    - Each rule has: id, name, priority, conditions, action
    - Each condition has: field, operator, value
    - action.type is one of VALID_ACTION_TYPES
    - priority is a positive integer

    Raises:
        FileNotFoundError: if path doesn't exist
        ValueError: if any rule is malformed
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")

    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    return load_rules_from_dict(data)


def load_rules_from_dict(data: list[dict]) -> list[Rule]:
    """
    Parse a list of rule dicts into Rule objects.
    Raises ValueError with helpful message if any rule is malformed.
    """
    if not isinstance(data, list):
        raise ValueError("Rules data must be a JSON array")

    rules = []
    for i, raw in enumerate(data):
        if not isinstance(raw, dict):
            raise ValueError(f"Rule {i}: must be a dictionary")

        for key in ('id', 'name', 'priority', 'conditions', 'action'):
            if key not in raw:
                raise ValueError(f"Rule {i}: missing key '{key}'")

        priority = raw['priority']
        if not isinstance(priority, int) or priority <= 0:
            raise ValueError(f"Rule {i}: priority must be a positive integer (got {priority})")

        conditions_raw = raw['conditions']
        if not isinstance(conditions_raw, list):
            raise ValueError(f"Rule {i}: conditions must be a list")

        conditions = []
        for j, cond_raw in enumerate(conditions_raw):
            if not isinstance(cond_raw, dict):
                raise ValueError(f"Rule {i}, condition {j}: condition must be a dict")
            for ckey in ('field', 'operator', 'value'):
                if ckey not in cond_raw:
                    raise ValueError(f"Rule {i}, condition {j}: missing key '{ckey}'")

            conditions.append(Condition(
                field=cond_raw['field'],
                operator=cond_raw['operator'],
                value=cond_raw['value']
            ))

        action_raw = raw['action']
        if not isinstance(action_raw, dict):
            raise ValueError(f"Rule {i}: action must be a dictionary")
        if 'type' not in action_raw:
            raise ValueError(f"Rule {i}: action missing 'type' key")

        action_type = action_raw['type']
        if action_type not in VALID_ACTION_TYPES:
            raise ValueError(f"Rule {i}: invalid action type '{action_type}'")

        if 'data' in action_raw and isinstance(action_raw['data'], dict):
            action_data = action_raw['data']
        else:
            action_data = {k: v for k, v in action_raw.items() if k != 'type'}

        action = Action(type=action_type, data=action_data)

        rules.append(Rule(
            id=raw['id'],
            name=raw['name'],
            priority=priority,
            conditions=conditions,
            action=action
        ))

    return rules
