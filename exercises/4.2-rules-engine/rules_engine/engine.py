"""
rules_engine/engine.py — Rules Engine Implementation for Exercise 4.2
"""
from dataclasses import dataclass, field
from typing import Any, Optional


VALID_OPERATORS = frozenset([
    'eq', 'ne', 'gt', 'gte', 'lt', 'lte',
    'in', 'not_in', 'contains', 'startswith'
])

VALID_ACTION_TYPES = frozenset([
    'route', 'voicemail', 'escalate', 'hangup', 'play_message'
])


@dataclass
class Condition:
    field: str
    operator: str
    value: Any

    def evaluate(self, context: dict) -> bool:
        """
        Evaluate this condition against the given context dict.

        Returns False if the field is not in context.
        Raises ValueError for unknown operators.

        Supported operators:
            eq, ne, gt, gte, lt, lte,
            in, not_in, contains, startswith
        """
        if self.operator not in VALID_OPERATORS:
            raise ValueError(
                f"Unknown operator '{self.operator}'. "
                f"Valid operators: {sorted(VALID_OPERATORS)}"
            )

        if self.field not in context:
            return False

        actual_val = context[self.field]

        if self.operator == 'eq':
            return actual_val == self.value
        elif self.operator == 'ne':
            return actual_val != self.value
        elif self.operator == 'gt':
            return actual_val > self.value
        elif self.operator == 'gte':
            return actual_val >= self.value
        elif self.operator == 'lt':
            return actual_val < self.value
        elif self.operator == 'lte':
            return actual_val <= self.value
        elif self.operator == 'in':
            try:
                return actual_val in self.value
            except TypeError:
                return False
        elif self.operator == 'not_in':
            try:
                return actual_val not in self.value
            except TypeError:
                return True
        elif self.operator == 'contains':
            try:
                return self.value in actual_val
            except TypeError:
                return False
        elif self.operator == 'startswith':
            return str(actual_val).startswith(str(self.value))

        raise ValueError(f"Unhandled operator: {self.operator}")


@dataclass
class Action:
    type: str
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.type not in VALID_ACTION_TYPES:
            raise ValueError(
                f"Invalid action type '{self.type}'. "
                f"Valid types: {sorted(VALID_ACTION_TYPES)}"
            )


@dataclass
class Rule:
    id: str
    name: str
    priority: int
    conditions: list[Condition]
    action: Action

    def matches(self, context: dict) -> bool:
        """
        Return True if ALL conditions evaluate to True.
        An empty conditions list always returns True (matches everything).
        """
        if not self.conditions:
            return True
        return all(cond.evaluate(context) for cond in self.conditions)


class RulesEngine:
    def __init__(self, rules: list[Rule]):
        # Rules sorted by priority (ascending — lower number = higher priority)
        self.rules = sorted(rules, key=lambda r: r.priority)

    def evaluate(self, context: dict) -> Optional[Action]:
        """
        Evaluate rules in priority order.
        Return the action of the FIRST matching rule.
        Return None if no rule matches.
        """
        for rule in self.rules:
            if rule.matches(context):
                return rule.action
        return None

    def evaluate_all(self, context: dict) -> list[tuple[Rule, Action]]:
        """
        Return all matching rules as (Rule, Action) tuples.
        Used for debugging and audit mode.
        """
        matches: list[tuple[Rule, Action]] = []
        for rule in self.rules:
            if rule.matches(context):
                matches.append((rule, rule.action))
        return matches


def evaluate_rules(event: dict, rules: list[dict]) -> list[str]:
    """
    Simplified rules evaluator function matching Exercise 4.2 task requirements.

    Input:
        event: An event dict like:
            {"event": "record_created", "record_type": "appointment", "status": "booked"}
        rules: Defined as Python dicts like:
            [
                {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"},
                {"condition": {"field": "record_type", "equals": "lead"}, "action": "assign_agent"},
            ]

    Output:
        A list of actions that matched.
    """
    matched_actions: list[str] = []

    if not isinstance(event, dict) or not isinstance(rules, list):
        return matched_actions

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        action = rule.get("action")
        if action is None:
            continue

        condition = rule.get("condition")

        # Empty or absent condition matches unconditionally
        if not condition:
            matched_actions.append(action if isinstance(action, str) else str(action))
            continue

        conditions = condition if isinstance(condition, list) else [condition]
        all_matched = True

        for cond in conditions:
            if not isinstance(cond, dict):
                all_matched = False
                break

            field_name = cond.get("field")
            if not field_name or field_name not in event:
                all_matched = False
                break

            # Handle "equals" key
            if "equals" in cond:
                if event[field_name] != cond["equals"]:
                    all_matched = False
                    break
            # Handle operator key
            elif "operator" in cond:
                op = cond["operator"]
                val = cond.get("value")
                try:
                    c = Condition(field=field_name, operator=op, value=val)
                    if not c.evaluate(event):
                        all_matched = False
                        break
                except Exception:
                    all_matched = False
                    break
            else:
                all_matched = False
                break

        if all_matched:
            matched_actions.append(action if isinstance(action, str) else str(action))

    return matched_actions
