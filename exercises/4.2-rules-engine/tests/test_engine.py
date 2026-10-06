"""
tests/test_engine.py — Starter test file for Exercise 4.2

TODO: Implement all test cases. Add at least 15 total tests.
Run with: pytest tests/ -v
"""
import pytest
from rules_engine.engine import Condition, Rule, Action, RulesEngine


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

    def test_missing_field_returns_false(self):
        cond = Condition(field='nonexistent', operator='eq', value='anything')
        assert cond.evaluate({}) is False

    def test_unknown_operator_raises_value_error(self):
        cond = Condition(field='x', operator='INVALID_OP', value=1)
        with pytest.raises(ValueError, match="Unknown operator"):
            cond.evaluate({'x': 1})

    def test_gt_operator_true(self):
        cond = Condition(field='call_count', operator='gt', value=3)
        assert cond.evaluate({'call_count': 4}) is True

    def test_gt_operator_false(self):
        cond = Condition(field='call_count', operator='gt', value=3)
        assert cond.evaluate({'call_count': 3}) is False  # not strictly greater

    def test_in_operator_match(self):
        cond = Condition(field='tag', operator='in', value=['VIP', 'PREMIUM'])
        assert cond.evaluate({'tag': 'VIP'}) is True

    def test_in_operator_no_match(self):
        cond = Condition(field='tag', operator='in', value=['VIP', 'PREMIUM'])
        assert cond.evaluate({'tag': 'STANDARD'}) is False

    def test_not_in_operator(self):
        cond = Condition(field='tag', operator='not_in', value=['BLOCKED'])
        assert cond.evaluate({'tag': 'VIP'}) is True
        assert cond.evaluate({'tag': 'BLOCKED'}) is False

    def test_contains_operator(self):
        cond = Condition(field='notes', operator='contains', value='urgent')
        assert cond.evaluate({'notes': 'This is an urgent matter'}) is True
        assert cond.evaluate({'notes': 'Normal inquiry'}) is False

    def test_gte_operator(self):
        cond = Condition(field='age', operator='gte', value=18)
        assert cond.evaluate({'age': 18}) is True
        assert cond.evaluate({'age': 19}) is True
        assert cond.evaluate({'age': 17}) is False

    def test_lte_operator(self):
        cond = Condition(field='age', operator='lte', value=18)
        assert cond.evaluate({'age': 18}) is True
        assert cond.evaluate({'age': 17}) is True
        assert cond.evaluate({'age': 19}) is False

    def test_lt_operator(self):
        cond = Condition(field='age', operator='lt', value=18)
        assert cond.evaluate({'age': 17}) is True
        assert cond.evaluate({'age': 18}) is False

    def test_ne_operator(self):
        cond = Condition(field='status', operator='ne', value='active')
        assert cond.evaluate({'status': 'inactive'}) is True
        assert cond.evaluate({'status': 'active'}) is False

    def test_startswith_operator(self):
        cond = Condition(field='phone', operator='startswith', value='+1')
        assert cond.evaluate({'phone': '+14155552671'}) is True
        assert cond.evaluate({'phone': '+447911123456'}) is False
        assert cond.evaluate({'phone': 12345}) is False  # not a string


# ─── Rule Tests ───────────────────────────────────────────────────

class TestRule:

    def test_all_conditions_must_match(self, vip_rule):
        # VIP rule has one condition: caller_tag in ['VIP', 'PREMIUM']
        assert vip_rule.matches({'caller_tag': 'VIP'}) is True

    def test_any_failing_condition_returns_false(self):
        rule = Rule(
            id='r', name='test', priority=1,
            conditions=[
                Condition('a', 'eq', 1),
                Condition('b', 'eq', 2),  # This will fail
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


# ─── RulesEngine Tests ────────────────────────────────────────────

class TestRulesEngine:

    def test_vip_bypass_scenario(self, vip_rule, after_hours_rule):
        engine = RulesEngine([after_hours_rule, vip_rule])  # deliberately out of priority order
        action = engine.evaluate({'caller_tag': 'VIP', 'hour_of_day': 22})
        assert action is not None
        assert action.type == 'route'  # VIP rule wins (priority 1 < 3)

    def test_no_match_returns_none(self, vip_rule):
        engine = RulesEngine([vip_rule])
        action = engine.evaluate({'caller_tag': 'STANDARD', 'hour_of_day': 14})
        assert action is None

    def test_rules_evaluated_in_priority_order(self, vip_rule, after_hours_rule, repeat_caller_rule):
        engine = RulesEngine([repeat_caller_rule, after_hours_rule, vip_rule])
        # VIP caller (priority 1 should win over repeat-caller priority 5)
        action = engine.evaluate({'caller_tag': 'VIP', 'call_count': 10, 'hour_of_day': 14})
        assert action.type == 'route'

    def test_evaluate_all_returns_all_matches(self, vip_rule, after_hours_rule):
        engine = RulesEngine([vip_rule, after_hours_rule])
        # VIP caller after hours — both rules match
        results = engine.evaluate_all({'caller_tag': 'VIP', 'hour_of_day': 22})
        assert len(results) == 2

    def test_standalone_evaluate_rules_function(self, vip_rule, after_hours_rule):
        from rules_engine.engine import evaluate_rules
        action = evaluate_rules({'caller_tag': 'VIP', 'hour_of_day': 14}, [after_hours_rule, vip_rule])
        assert action is not None
        assert action.type == 'route'
