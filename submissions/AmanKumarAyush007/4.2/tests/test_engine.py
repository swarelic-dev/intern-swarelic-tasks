import json
import pytest
from rules_engine import Action, Condition, Rule, RulesEngine, load_rules_from_dict, load_rules_from_json


@pytest.mark.parametrize(("operator", "actual", "value", "expected"), [
    ("eq", 4, 4, True), ("eq", 4, 5, False), ("ne", 4, 5, True),
    ("gt", 4, 3, True), ("gte", 4, 4, True), ("lt", 4, 5, True),
    ("lte", 4, 4, True), ("in", "VIP", ["VIP", "PREMIUM"], True),
    ("not_in", "STANDARD", ["VIP"], True), ("contains", ["VIP"], "VIP", True),
    ("startswith", "billing_request", "billing", True),
    ("gt", "incorrect", 3, False), ("contains", None, "a", False),
])
def test_operators(operator, actual, value, expected):
    assert Condition("field", operator, value).evaluate({"field": actual}) is expected


def test_missing_field_returns_false():
    assert Condition("missing", "ne", 0).evaluate({}) is False


def test_unknown_operator_raises():
    with pytest.raises(ValueError):
        Condition("field", "unknown", 1).evaluate({})


def test_contains_on_list():
    assert Condition("tags", "contains", "VIP").evaluate({"tags": ["VIP"]})


def test_invalid_membership_operand():
    assert not Condition("tag", "in", "VIP").evaluate({"tag": "VIP"})


def test_rule_requires_all_conditions():
    rule = Rule("x", "all", 1, [Condition("a", "eq", 1), Condition("b", "eq", 2)], Action("route"))
    assert rule.matches({"a": 1, "b": 2})
    assert not rule.matches({"a": 1, "b": 3})


def test_empty_conditions_match():
    assert Rule("x", "all", 1, [], Action("route")).matches({})


def test_first_match_wins_and_priority_sorted():
    low = Rule("low", "low", 10, [], Action("hangup"))
    high = Rule("high", "high", 1, [], Action("route"))
    engine = RulesEngine([low, high])
    assert [rule.id for rule in engine.rules] == ["high", "low"]
    assert engine.evaluate({}).type == "route"
    assert [rule.id for rule, _ in engine.evaluate_all({})] == ["high", "low"]


def test_no_match():
    engine = RulesEngine([Rule("x", "x", 1, [Condition("x", "eq", 2)], Action("route"))])
    assert engine.evaluate({"x": 1}) is None


def test_vip_scenario():
    rules = load_rules_from_dict([{
        "id": "vip", "name": "VIP", "priority": 1,
        "conditions": [{"field": "caller_tag", "operator": "in", "value": ["VIP", "PREMIUM"]}],
        "action": {"type": "route", "target": "vip-queue"},
    }])
    assert RulesEngine(rules).evaluate({"caller_tag": "VIP"}).data["target"] == "vip-queue"


def test_json_round_trip(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps([{"id": "a", "name": "A", "priority": 1,
       "conditions": [], "action": {"type": "hangup"}}]), encoding="utf-8")
    assert load_rules_from_json(path)[0].action.type == "hangup"


def test_missing_rule_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_rules_from_json(tmp_path / "not-found.json")


def test_duplicate_id_rejected():
    item = {"id": "a", "name": "A", "priority": 1, "conditions": [], "action": {"type": "hangup"}}
    with pytest.raises(ValueError, match="unique"):
        load_rules_from_dict([item, item])


def test_invalid_action_rejected():
    with pytest.raises(ValueError):
        load_rules_from_dict([{"id": "a", "name": "A", "priority": 1,
                               "conditions": [], "action": {"type": "unknown"}}])




def test_equal_priority_preserves_original_rule_order():
    """Rules with equal priority must retain their insertion order."""
    first_rule = Rule(
        id="rule-first",
        name="First rule",
        priority=1,
        conditions=[],
        action=Action(type="route", data={"target": "sales"}),
    )
    second_rule = Rule(
        id="rule-second",
        name="Second rule",
        priority=1,
        conditions=[],
        action=Action(type="route", data={"target": "support"}),
    )

    engine = RulesEngine([first_rule, second_rule])

    assert [rule.id for rule in engine.rules] == [
        "rule-first",
        "rule-second",
    ]
    assert engine.evaluate({}) == first_rule.action


def test_evaluate_all_returns_empty_list_when_no_rules_match():
    """Return an empty result when no rule matches the context."""
    rule = Rule(
        id="rule-unmatched",
        name="Only premium callers",
        priority=1,
        conditions=[
            Condition(
                field="caller_tag",
                operator="eq",
                value="PREMIUM",
            )
        ],
        action=Action(type="route", data={"target": "premium-queue"}),
    )

    engine = RulesEngine([rule])

    assert engine.evaluate_all({"caller_tag": "STANDARD"}) == []
