"""Deterministic, side-effect-free evaluation of routing rules."""
from __future__ import annotations

import operator as op
from dataclasses import dataclass, field
from typing import Any, Mapping

_COMPARISONS = {"eq": op.eq, "ne": op.ne, "gt": op.gt, "gte": op.ge, "lt": op.lt, "lte": op.le}
_OPERATORS = frozenset((*_COMPARISONS, "in", "not_in", "contains", "startswith"))


@dataclass(frozen=True)
class Condition:
    """A single predicate evaluated against a call context."""

    field: str
    operator: str
    value: Any

    def evaluate(self, context: Mapping[str, Any]) -> bool:
        """Return whether the field meets this condition; absent fields never match."""
        if self.operator not in _OPERATORS:
            raise ValueError(f"Unsupported operator: {self.operator}")
        if self.field not in context:
            return False
        actual = context[self.field]
        if self.operator in _COMPARISONS:
            try:
                return bool(_COMPARISONS[self.operator](actual, self.value))
            except (TypeError, ValueError):
                return False
        if self.operator in ("in", "not_in"):
            if not isinstance(self.value, (list, tuple, set, frozenset)):
                return False
            try:
                matched = actual in self.value
            except TypeError:
                return False
            return matched if self.operator == "in" else not matched
        if self.operator == "contains":
            if not isinstance(actual, (str, list, tuple, set, frozenset)):
                return False
            try:
                return self.value in actual
            except TypeError:
                return False
        return isinstance(actual, str) and isinstance(self.value, str) and actual.startswith(self.value)


@dataclass(frozen=True)
class Action:
    """An action description; execution belongs to the calling application."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Rule:
    """A named, ordered conjunction of conditions."""

    id: str
    name: str
    priority: int
    conditions: list[Condition]
    action: Action

    def matches(self, context: Mapping[str, Any]) -> bool:
        """Match only when every condition passes (empty conjunction matches)."""
        return all(condition.evaluate(context) for condition in self.conditions)


class RulesEngine:
    """Evaluate rules in stable ascending priority order."""

    def __init__(self, rules: list[Rule]) -> None:
        self.rules = sorted(rules, key=lambda rule: rule.priority)

    def evaluate(self, context: Mapping[str, Any]) -> Action | None:
        """Return the first matching action, or None when no rules match."""
        for rule in self.rules:
            if rule.matches(context):
                return rule.action
        return None

    def evaluate_all(self, context: Mapping[str, Any]) -> list[tuple[Rule, Action]]:
        """Return ordered matches for audit and debugging purposes."""
        return [(rule, rule.action) for rule in self.rules if rule.matches(context)]
