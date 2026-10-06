"""
apps/rules/engine.py
~~~~~~~~~~~~~~~~~~~~
Mini Rules Engine for Exercise 4.2.

Evaluates a list of rule dicts against an event dict and returns every
action whose conditions all match.

Rule dict shape
---------------
{
    "condition": {"field": "<key>", "equals": "<value>"},
    "action":    "<action_name>"
}

Event dict shape
----------------
{
    "event":       "record_created",
    "record_type": "appointment",
    "status":      "booked"
}

Usage
-----
    from apps.rules.engine import evaluate_rules

    event = {"event": "record_created", "record_type": "appointment", "status": "booked"}
    rules = [
        {"condition": {"field": "status",      "equals": "booked"}, "action": "send_whatsapp"},
        {"condition": {"field": "record_type", "equals": "lead"},   "action": "assign_agent"},
    ]
    matched_actions = evaluate_rules(event, rules)
    # → ["send_whatsapp"]
"""

from __future__ import annotations

from typing import Any


# ──────────────────────────────────────────────────────────────────
# Core helpers
# ──────────────────────────────────────────────────────────────────

def _evaluate_condition(condition: dict[str, Any], event: dict[str, Any]) -> bool:
    """
    Evaluate a single condition dict against the event.

    A condition must have exactly two keys:
      - "field"  : the key to look up in the event
      - "equals" : the value that key must equal for the condition to match

    Returns False when:
      - the condition dict is missing "field" or "equals"
      - the event does not contain the specified field
      - the event's field value does not equal the expected value
    """
    field = condition.get("field")
    expected = condition.get("equals")

    # Guard: malformed condition
    if field is None or expected is None:
        return False

    # Guard: field absent from event
    if field not in event:
        return False

    return event[field] == expected


def _rule_matches(rule: dict[str, Any], event: dict[str, Any]) -> bool:
    """
    Return True if the rule's condition matches the event.

    A rule without a "condition" key never matches.
    A rule without an "action" key is ignored (returns False).
    """
    if "condition" not in rule or "action" not in rule:
        return False

    return _evaluate_condition(rule["condition"], event)


# ──────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────

def evaluate_rules(event: dict[str, Any], rules: list[dict[str, Any]]) -> list[str]:
    """
    Evaluate *event* against every rule in *rules*.

    Parameters
    ----------
    event : dict
        The incoming event payload (arbitrary key/value pairs).
    rules : list[dict]
        List of rule dicts, each with ``"condition"`` and ``"action"`` keys.

    Returns
    -------
    list[str]
        Ordered list of action names for every rule whose condition matched.
        Returns an empty list when no rules match.

    Examples
    --------
    >>> event = {"status": "booked", "record_type": "appointment"}
    >>> rules = [
    ...     {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"},
    ...     {"condition": {"field": "record_type", "equals": "lead"}, "action": "assign_agent"},
    ... ]
    >>> evaluate_rules(event, rules)
    ['send_whatsapp']
    """
    matched: list[str] = []

    for rule in rules:
        if _rule_matches(rule, event):
            matched.append(rule["action"])

    return matched
