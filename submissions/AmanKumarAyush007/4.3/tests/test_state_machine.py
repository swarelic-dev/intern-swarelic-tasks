import pytest
from agent_flow import AgentEvent as E, AgentState as S, AgentSession, AgentStateMachine, InvalidTransitionError


@pytest.fixture
def machine():
    return AgentStateMachine("alice")


def test_login_from_offline(machine):
    assert machine.trigger(E.LOGIN) == S.ONLINE


def test_ready_from_online(machine):
    machine.trigger(E.LOGIN)
    assert machine.trigger(E.READY) == S.AVAILABLE


def test_call_received_from_available(machine):
    machine.trigger(E.LOGIN); machine.trigger(E.READY)
    assert machine.trigger(E.CALL_RECEIVED, call_id="a") == S.RINGING


def test_call_accepted_from_ringing(machine):
    machine.trigger(E.LOGIN); machine.trigger(E.READY); machine.trigger(E.CALL_RECEIVED, call_id="x")
    assert machine.trigger(E.CALL_ACCEPTED) == S.ON_CALL


def test_call_ended_from_on_call(machine):
    machine.trigger(E.LOGIN); machine.trigger(E.READY); machine.trigger(E.CALL_RECEIVED, call_id="x")
    machine.trigger(E.CALL_ACCEPTED)
    assert machine.trigger(E.CALL_ENDED) == S.WRAPPING_UP


def test_wrap_up_done_from_wrapping_up(machine):
    for event in (E.LOGIN, E.READY): machine.trigger(event)
    machine.trigger(E.CALL_RECEIVED, call_id="x")
    for event in (E.CALL_ACCEPTED, E.CALL_ENDED): machine.trigger(event)
    assert machine.trigger(E.WRAP_UP_DONE) == S.AVAILABLE


def test_full_happy_path(machine):
    machine.trigger(E.LOGIN); machine.trigger(E.READY); machine.trigger(E.CALL_RECEIVED, call_id="x")
    machine.trigger(E.CALL_ACCEPTED); machine.trigger(E.CALL_ENDED); machine.trigger(E.WRAP_UP_DONE)
    assert machine.state == S.AVAILABLE and len(machine.get_history()) == 6


def test_cannot_accept_from_offline(machine):
    with pytest.raises(InvalidTransitionError): machine.trigger(E.CALL_ACCEPTED)


def test_cannot_enter_call_directly(machine):
    with pytest.raises(InvalidTransitionError): machine.trigger(E.CALL_ENDED)


def test_invalid_event_does_not_change_history(machine):
    with pytest.raises(InvalidTransitionError): machine.trigger(E.WRAP_UP_DONE)
    assert machine.get_history() == []


def test_missing_call_id_rejected(machine):
    machine.trigger(E.LOGIN); machine.trigger(E.READY)
    with pytest.raises(InvalidTransitionError): machine.trigger(E.CALL_RECEIVED)


def test_reject_call(machine):
    machine.trigger(E.LOGIN); machine.trigger(E.READY); machine.trigger(E.CALL_RECEIVED, call_id="x")
    assert machine.trigger(E.CALL_REJECTED) == S.AVAILABLE


def test_break_cycle(machine):
    machine.trigger(E.LOGIN); machine.trigger(E.READY)
    assert machine.trigger(E.TAKE_BREAK) == S.BREAK
    assert machine.trigger(E.END_BREAK) == S.AVAILABLE


def test_can_trigger(machine):
    assert machine.can_trigger(E.LOGIN)
    assert not machine.can_trigger(E.CALL_ACCEPTED)


def test_history_is_defensive_copy(machine):
    machine.trigger(E.LOGIN, origin="web")
    history = machine.get_history(); history[0]["metadata"]["origin"] = "changed"
    assert machine.get_history()[0]["metadata"]["origin"] == "web"


def test_calls_handled_increments():
    session = AgentSession("alice")
    session.process_event(E.LOGIN); session.process_event(E.READY)
    session.process_event(E.CALL_RECEIVED, call_id="x")
    session.process_event(E.CALL_ACCEPTED); session.process_event(E.CALL_ENDED)
    assert session.get_metrics()["calls_handled"] == 1


def test_metrics_structure():
    metrics = AgentSession("alice").get_metrics()
    assert set(metrics) == {"session_duration_secs", "calls_handled", "avg_call_duration_secs", "availability_pct", "current_state"}
    assert metrics["availability_pct"] == 0
