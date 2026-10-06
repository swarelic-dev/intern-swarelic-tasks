"""
tests/test_engine.py
~~~~~~~~~~~~~~~~~~~~
Unit tests for the Exercise 4.2 Rules Engine.

Run with:
    cd exercises/4.2-rules-engine
    pytest tests/ -v

Covers
------
- Basic match (single condition that matches)
- Basic no-match (single condition that does not match)
- Multiple rules — only matching ones returned
- Multiple rules — all match
- Multiple rules — none match  → empty list
- Edge: empty rules list
- Edge: empty event dict
- Edge: field missing from event
- Edge: malformed rule (missing "condition" key)
- Edge: malformed rule (missing "action" key)
- Edge: malformed condition (missing "field" key)
- Edge: malformed condition (missing "equals" key)
- Exact task-spec example from the exercise prompt
"""

import pytest
from rules_engine.engine import evaluate_rules


# ──────────────────────────────────────────────────────────────────
# Fixtures — reusable rule and event objects
# ──────────────────────────────────────────────────────────────────

@pytest.fixture
def booked_event():
    """The example event from the exercise prompt."""
    return {
        "event": "record_created",
        "record_type": "appointment",
        "status": "booked",
    }


@pytest.fixture
def lead_event():
    return {
        "event": "record_created",
        "record_type": "lead",
        "status": "new",
    }


@pytest.fixture
def send_whatsapp_rule():
    return {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"}


@pytest.fixture
def assign_agent_rule():
    return {"condition": {"field": "record_type", "equals": "lead"}, "action": "assign_agent"}


@pytest.fixture
def send_email_rule():
    return {"condition": {"field": "status", "equals": "booked"}, "action": "send_email"}


# ──────────────────────────────────────────────────────────────────
# Test 1 — Basic match: single matching rule returns its action
# ──────────────────────────────────────────────────────────────────

def test_single_rule_matches(booked_event, send_whatsapp_rule):
    result = evaluate_rules(booked_event, [send_whatsapp_rule])
    assert result == ["send_whatsapp"]


# ──────────────────────────────────────────────────────────────────
# Test 2 — Basic no-match: condition field value differs
# ──────────────────────────────────────────────────────────────────

def test_single_rule_no_match(booked_event, assign_agent_rule):
    # event has record_type="appointment", rule expects "lead"
    result = evaluate_rules(booked_event, [assign_agent_rule])
    assert result == []


# ──────────────────────────────────────────────────────────────────
# Test 3 — Exact exercise-prompt example
# ──────────────────────────────────────────────────────────────────

def test_exercise_prompt_example():
    """
    Reproduces the exact scenario from the task description:
      event  = {event, record_type=appointment, status=booked}
      rules  = [status==booked → send_whatsapp, record_type==lead → assign_agent]
      output = ["send_whatsapp"]
    """
    event = {
        "event": "record_created",
        "record_type": "appointment",
        "status": "booked",
    }
    rules = [
        {"condition": {"field": "status",      "equals": "booked"}, "action": "send_whatsapp"},
        {"condition": {"field": "record_type", "equals": "lead"},   "action": "assign_agent"},
    ]
    result = evaluate_rules(event, rules)
    assert result == ["send_whatsapp"]


# ──────────────────────────────────────────────────────────────────
# Test 4 — Multiple rules all match → all actions returned in order
# ──────────────────────────────────────────────────────────────────

def test_multiple_rules_all_match(booked_event, send_whatsapp_rule, send_email_rule):
    rules = [send_whatsapp_rule, send_email_rule]
    result = evaluate_rules(booked_event, rules)
    assert result == ["send_whatsapp", "send_email"]


# ──────────────────────────────────────────────────────────────────
# Test 5 — Only some rules match → only matched actions returned
# ──────────────────────────────────────────────────────────────────

def test_partial_match_returns_only_matched(booked_event, send_whatsapp_rule, assign_agent_rule):
    rules = [send_whatsapp_rule, assign_agent_rule]
    result = evaluate_rules(booked_event, rules)
    assert "send_whatsapp" in result
    assert "assign_agent" not in result


# ──────────────────────────────────────────────────────────────────
# Test 6 — No rules match → empty list (not None)
# ──────────────────────────────────────────────────────────────────

def test_no_rules_match_returns_empty_list(assign_agent_rule):
    event = {"record_type": "appointment"}   # does not match "lead"
    result = evaluate_rules(event, [assign_agent_rule])
    assert result == []
    assert isinstance(result, list)


# ──────────────────────────────────────────────────────────────────
# Test 7 — Empty rules list → always returns empty list
# ──────────────────────────────────────────────────────────────────

def test_empty_rules_list(booked_event):
    result = evaluate_rules(booked_event, [])
    assert result == []


# ──────────────────────────────────────────────────────────────────
# Test 8 — Empty event dict → nothing can match → empty list
# ──────────────────────────────────────────────────────────────────

def test_empty_event(send_whatsapp_rule):
    result = evaluate_rules({}, [send_whatsapp_rule])
    assert result == []


# ──────────────────────────────────────────────────────────────────
# Test 9 — Field missing from event → no match (not an error)
# ──────────────────────────────────────────────────────────────────

def test_missing_field_in_event_does_not_raise():
    event = {"record_type": "appointment"}   # "status" is missing
    rule  = {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"}
    result = evaluate_rules(event, [rule])
    assert result == []


# ──────────────────────────────────────────────────────────────────
# Test 10 — Malformed rule: missing "condition" key → skipped silently
# ──────────────────────────────────────────────────────────────────

def test_rule_missing_condition_key_is_skipped():
    event = {"status": "booked"}
    rule  = {"action": "send_whatsapp"}          # no "condition"
    result = evaluate_rules(event, [rule])
    assert result == []


# ──────────────────────────────────────────────────────────────────
# Test 11 — Malformed rule: missing "action" key → skipped silently
# ──────────────────────────────────────────────────────────────────

def test_rule_missing_action_key_is_skipped():
    event = {"status": "booked"}
    rule  = {"condition": {"field": "status", "equals": "booked"}}  # no "action"
    result = evaluate_rules(event, [rule])
    assert result == []


# ──────────────────────────────────────────────────────────────────
# Test 12 — Malformed condition: missing "field" key → no match
# ──────────────────────────────────────────────────────────────────

def test_condition_missing_field_key():
    event = {"status": "booked"}
    rule  = {"condition": {"equals": "booked"}, "action": "send_whatsapp"}
    result = evaluate_rules(event, [rule])
    assert result == []


# ──────────────────────────────────────────────────────────────────
# Test 13 — Malformed condition: missing "equals" key → no match
# ──────────────────────────────────────────────────────────────────

def test_condition_missing_equals_key():
    event = {"status": "booked"}
    rule  = {"condition": {"field": "status"}, "action": "send_whatsapp"}
    result = evaluate_rules(event, [rule])
    assert result == []


# ──────────────────────────────────────────────────────────────────
# Test 14 — Case sensitivity: "Booked" ≠ "booked"
# ──────────────────────────────────────────────────────────────────

def test_condition_is_case_sensitive():
    event = {"status": "Booked"}  # capital B
    rule  = {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"}
    result = evaluate_rules(event, [rule])
    assert result == []


# ──────────────────────────────────────────────────────────────────
# Test 15 — Mixed valid and malformed rules → only valid matches returned
# ──────────────────────────────────────────────────────────────────

def test_mixed_valid_and_malformed_rules():
    event = {"status": "booked"}
    rules = [
        {"action": "orphan_action"},                                         # no condition
        {"condition": {"field": "status", "equals": "booked"}, "action": "send_whatsapp"},
        {"condition": {"field": "status"}},                                  # no action
    ]
    result = evaluate_rules(event, rules)
    assert result == ["send_whatsapp"]
