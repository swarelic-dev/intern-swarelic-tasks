"""
tests/test_engine.py — Comprehensive Unit Test Suite for Exercise 4.2
"""
import pytest
from pathlib import Path
from rules_engine.engine import (
    Condition,
    Rule,
    Action,
    RulesEngine,
    evaluate_rules,
)
from rules_engine.loader import load_rules_from_json, load_rules_from_dict


# ─── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def vip_rule():
    return Rule(
        id='rule-001',
        name='VIP Bypass',
        priority=1,
        conditions=[
            Condition(field='caller_tag', operator='in', value=['VIP', 'PREMIUM'])
        ],
        action=Action(type='route', data={'target': 'vip-queue'})
    )


@pytest.fixture
def after_hours_rule():
    return Rule(
        id='rule-003',
        name='After Hours',
        priority=3,
        conditions=[
            Condition(field='hour_of_day', operator='gte', value=21)
        ],
        action=Action(type='voicemail', data={'message': 'We are closed.'})
    )


@pytest.fixture
def repeat_caller_rule():
    return Rule(
        id='rule-005',
        name='Repeat Caller',
        priority=5,
        conditions=[
            Condition(field='call_count', operator='gt', value=3)
        ],
        action=Action(type='escalate', data={'target': 'supervisor'})
    )


# ─── Condition Tests ──────────────────────────────────────────────

class TestCondition:

    def test_eq_operator_match(self):
        cond = Condition(field='status', operator='eq', value='active')
        assert cond.evaluate({'status': 'active'}) is True

    def test_eq_operator_no_match(self):
        cond = Condition(field='status', operator='eq', value='active')
        assert cond.evaluate({'status': 'inactive'}) is False

    def test_ne_operator(self):
        cond = Condition(field='status', operator='ne', value='blocked')
        assert cond.evaluate({'status': 'active'}) is True
        assert cond.evaluate({'status': 'blocked'}) is False

    def test_missing_field_returns_false(self):
        cond = Condition(field='nonexistent', operator='eq', value='anything')
        assert cond.evaluate({}) is False

    def test_unknown_operator_raises_value_error(self):
        cond = Condition(field='x', operator='INVALID_OP', value=1)
        with pytest.raises(ValueError, match="Unknown operator"):
            cond.evaluate({'x': 1})

    def test_gt_operator(self):
        cond = Condition(field='call_count', operator='gt', value=3)
        assert cond.evaluate({'call_count': 4}) is True
        assert cond.evaluate({'call_count': 3}) is False
        assert cond.evaluate({'call_count': 2}) is False

    def test_gte_operator(self):
        cond = Condition(field='hour_of_day', operator='gte', value=21)
        assert cond.evaluate({'hour_of_day': 21}) is True
        assert cond.evaluate({'hour_of_day': 22}) is True
        assert cond.evaluate({'hour_of_day': 20}) is False

    def test_lt_operator(self):
        cond = Condition(field='wait_time', operator='lt', value=30)
        assert cond.evaluate({'wait_time': 25}) is True
        assert cond.evaluate({'wait_time': 30}) is False

    def test_lte_operator(self):
        cond = Condition(field='score', operator='lte', value=50)
        assert cond.evaluate({'score': 50}) is True
        assert cond.evaluate({'score': 49}) is True
        assert cond.evaluate({'score': 51}) is False

    def test_in_operator(self):
        cond = Condition(field='tag', operator='in', value=['VIP', 'PREMIUM'])
        assert cond.evaluate({'tag': 'VIP'}) is True
        assert cond.evaluate({'tag': 'PREMIUM'}) is True
        assert cond.evaluate({'tag': 'STANDARD'}) is False

    def test_not_in_operator(self):
        cond = Condition(field='tag', operator='not_in', value=['BLOCKED', 'SPAM'])
        assert cond.evaluate({'tag': 'VIP'}) is True
        assert cond.evaluate({'tag': 'BLOCKED'}) is False

    def test_contains_operator(self):
        cond = Condition(field='notes', operator='contains', value='urgent')
        assert cond.evaluate({'notes': 'This is an urgent matter'}) is True
        assert cond.evaluate({'notes': 'Normal inquiry'}) is False

    def test_startswith_operator(self):
        cond = Condition(field='phone', operator='startswith', value='+1')
        assert cond.evaluate({'phone': '+18005550100'}) is True
        assert cond.evaluate({'phone': '+44207123456'}) is False


# ─── Rule Tests ───────────────────────────────────────────────────

class TestRule:

    def test_all_conditions_must_match(self, vip_rule):
        assert vip_rule.matches({'caller_tag': 'VIP'}) is True

    def test_any_failing_condition_returns_false(self):
        rule = Rule(
            id='r', name='test', priority=1,
            conditions=[
                Condition('a', 'eq', 1),
                Condition('b', 'eq', 2),
            ],
            action=Action(type='hangup')
        )
        assert rule.matches({'a': 1, 'b': 99}) is False

    def test_empty_conditions_always_matches(self):
        rule = Rule(
            id='r', name='catch-all', priority=99,
            conditions=[],
            action=Action(type='route', data={'target': 'default-queue'})
        )
        assert rule.matches({}) is True
        assert rule.matches({'anything': 'here'}) is True

    def test_invalid_action_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid action type"):
            Action(type='unsupported_action')


# ─── RulesEngine Tests ────────────────────────────────────────────

class TestRulesEngine:

    def test_vip_bypass_scenario(self, vip_rule, after_hours_rule):
        engine = RulesEngine([after_hours_rule, vip_rule])
        action = engine.evaluate({'caller_tag': 'VIP', 'hour_of_day': 22})
        assert action is not None
        assert action.type == 'route'

    def test_no_match_returns_none(self, vip_rule):
        engine = RulesEngine([vip_rule])
        action = engine.evaluate({'caller_tag': 'STANDARD', 'hour_of_day': 14})
        assert action is None

    def test_rules_evaluated_in_priority_order(self, vip_rule, after_hours_rule, repeat_caller_rule):
        engine = RulesEngine([repeat_caller_rule, after_hours_rule, vip_rule])
        action = engine.evaluate({'caller_tag': 'VIP', 'call_count': 10, 'hour_of_day': 14})
        assert action.type == 'route'

    def test_evaluate_all_returns_all_matches(self, vip_rule, after_hours_rule):
        engine = RulesEngine([vip_rule, after_hours_rule])
        results = engine.evaluate_all({'caller_tag': 'VIP', 'hour_of_day': 22})
        assert len(results) == 2


# ─── Loader Tests ─────────────────────────────────────────────────

class TestLoader:

    def test_load_from_dict_valid(self):
        raw = [
            {
                "id": "r1",
                "name": "Rule 1",
                "priority": 1,
                "conditions": [{"field": "status", "operator": "eq", "value": "active"}],
                "action": {"type": "route", "target": "queue-1"}
            }
        ]
        rules = load_rules_from_dict(raw)
        assert len(rules) == 1
        assert rules[0].id == "r1"
        assert rules[0].action.type == "route"

    def test_load_from_dict_missing_key(self):
        raw = [{"id": "r1", "name": "Rule 1"}]  # missing priority, conditions, action
        with pytest.raises(ValueError, match="missing key"):
            load_rules_from_dict(raw)

    def test_load_from_dict_invalid_priority(self):
        raw = [{
            "id": "r1", "name": "R1", "priority": -5,
            "conditions": [], "action": {"type": "hangup"}
        }]
        with pytest.raises(ValueError, match="positive integer"):
            load_rules_from_dict(raw)

    def test_load_from_json_file(self, tmp_path):
        sample_path = Path(__file__).parent.parent / "sample_rules.json"
        if sample_path.exists():
            rules = load_rules_from_json(sample_path)
            assert len(rules) >= 6

    def test_load_from_json_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_rules_from_json("non_existent_rules_file.json")


# ─── Prompt evaluate_rules Function Tests ─────────────────────────

class TestEvaluateRulesFunction:

    def test_prompt_spec_example(self):
        event = {
            "event": "record_created",
            "record_type": "appointment",
            "status": "booked"
        }
        rules = [
            {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"},
            {"condition": {"field": "record_type", "equals": "lead"}, "action": "assign_agent"},
        ]
        matched = evaluate_rules(event, rules)
        assert matched == ["send_whatsapp"]

    def test_evaluate_rules_multiple_matches(self):
        event = {
            "record_type": "appointment",
            "status": "booked",
            "vip": True
        }
        rules = [
            {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"},
            {"condition": {"field": "record_type", "equals": "appointment"}, "action": "notify_calendar"},
            {"condition": {"field": "record_type", "equals": "lead"}, "action": "assign_agent"},
        ]
        matched = evaluate_rules(event, rules)
        assert matched == ["send_whatsapp", "notify_calendar"]

    def test_evaluate_rules_no_match(self):
        event = {"status": "cancelled", "record_type": "inquiry"}
        rules = [
            {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"},
            {"condition": {"field": "record_type", "equals": "lead"}, "action": "assign_agent"},
        ]
        matched = evaluate_rules(event, rules)
        assert matched == []

    def test_evaluate_rules_missing_field_in_event(self):
        event = {"timestamp": "2026-10-09T12:00:00Z"}
        rules = [
            {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"}
        ]
        assert evaluate_rules(event, rules) == []

    def test_evaluate_rules_empty_rules_and_events(self):
        assert evaluate_rules({}, []) == []
        assert evaluate_rules({"status": "booked"}, []) == []

    def test_evaluate_rules_malformed_rule_resilience(self):
        event = {"status": "booked"}
        rules = [
            "not a dict",
            {"missing_condition_and_action": True},
            {"condition": None, "action": "fallback_action"},
            {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"},
        ]
        matched = evaluate_rules(event, rules)
        assert matched == ["fallback_action", "send_whatsapp"]
