"""
rules_engine/engine.py — Starter for Exercise 4.2

TODO: Implement Condition.evaluate(), Rule.matches(), 
      RulesEngine.evaluate(), and RulesEngine.evaluate_all()

See docs/02-rules-engine.md for full requirements.
"""
from dataclasses import dataclass, field
from typing import Any


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

        # YOUR CODE HERE
        ctx_val = context[self.field]
        
        if self.operator == 'eq':
            return ctx_val == self.value
        elif self.operator == 'ne':
            return ctx_val != self.value
        elif self.operator == 'gt':
            return ctx_val > self.value
        elif self.operator == 'gte':
            return ctx_val >= self.value
        elif self.operator == 'lt':
            return ctx_val < self.value
        elif self.operator == 'lte':
            return ctx_val <= self.value
        elif self.operator == 'in':
            return ctx_val in self.value
        elif self.operator == 'not_in':
            return ctx_val not in self.value
        elif self.operator == 'contains':
            return self.value in ctx_val
        elif self.operator == 'startswith':
            if not isinstance(ctx_val, str):
                return False
            return ctx_val.startswith(self.value)
            
        return False


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
        # YOUR CODE HERE
        for condition in self.conditions:
            if not condition.evaluate(context):
                return False
        return True


class RulesEngine:
    def __init__(self, rules: list[Rule]):
        # Rules sorted by priority (ascending — lower number = higher priority)
        self.rules = sorted(rules, key=lambda r: r.priority)

    def evaluate(self, context: dict) -> 'Action | None':
        """
        Evaluate rules in priority order.
        Return the action of the FIRST matching rule.
        Return None if no rule matches.
        """
        # YOUR CODE HERE
        for rule in self.rules:
            if rule.matches(context):
                return rule.action
        return None

    def evaluate_all(self, context: dict) -> 'list[tuple[Rule, Action]]':
        """
        Return all matching rules as (Rule, Action) tuples.
        Used for debugging and audit mode.
        """
        # YOUR CODE HERE
        return [(rule, rule.action) for rule in self.rules if rule.matches(context)]


def evaluate_rules(event: dict, rules: list[Rule]) -> 'Action | None':
    """
    Standalone function to evaluate an event against a list of rules.
    Matches the specific requirement from the exercise prompt.
    """
    engine = RulesEngine(rules)
    return engine.evaluate(event)
