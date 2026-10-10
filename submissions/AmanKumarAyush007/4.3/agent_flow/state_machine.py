"""Guarded, observable finite state machine for one agent."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable


class AgentState(Enum):
    OFFLINE = auto()
    ONLINE = auto()
    AVAILABLE = auto()
    RINGING = auto()
    ON_CALL = auto()
    WRAPPING_UP = auto()
    BREAK = auto()


class AgentEvent(Enum):
    LOGIN = auto()
    READY = auto()
    CALL_RECEIVED = auto()
    CALL_ACCEPTED = auto()
    CALL_REJECTED = auto()
    CALL_ENDED = auto()
    WRAP_UP_DONE = auto()
    TAKE_BREAK = auto()
    END_BREAK = auto()
    LOGOUT = auto()


class InvalidTransitionError(Exception):
    """An event is invalid for the current state or its guard fails."""


@dataclass(frozen=True)
class StateTransition:
    """One allowed state transition, with optional validation and callback."""

    from_state: AgentState
    event: AgentEvent
    to_state: AgentState
    guard: Callable[..., bool] | None = None
    on_enter: Callable[..., None] | None = None


class AgentStateMachine:
    """Model an agent's states without persisting or publishing external events."""

    TRANSITIONS: list[StateTransition] = [
        StateTransition(AgentState.OFFLINE, AgentEvent.LOGIN, AgentState.ONLINE),
        StateTransition(AgentState.ONLINE, AgentEvent.READY, AgentState.AVAILABLE),
        StateTransition(AgentState.ONLINE, AgentEvent.LOGOUT, AgentState.OFFLINE),
        StateTransition(AgentState.AVAILABLE, AgentEvent.CALL_RECEIVED, AgentState.RINGING),
        StateTransition(AgentState.RINGING, AgentEvent.CALL_ACCEPTED, AgentState.ON_CALL),
        StateTransition(AgentState.RINGING, AgentEvent.CALL_REJECTED, AgentState.AVAILABLE),
        StateTransition(AgentState.ON_CALL, AgentEvent.CALL_ENDED, AgentState.WRAPPING_UP),
        StateTransition(AgentState.WRAPPING_UP, AgentEvent.WRAP_UP_DONE, AgentState.AVAILABLE),
        StateTransition(AgentState.AVAILABLE, AgentEvent.TAKE_BREAK, AgentState.BREAK),
        StateTransition(AgentState.BREAK, AgentEvent.END_BREAK, AgentState.AVAILABLE),
        StateTransition(AgentState.AVAILABLE, AgentEvent.LOGOUT, AgentState.OFFLINE),
        StateTransition(AgentState.BREAK, AgentEvent.LOGOUT, AgentState.OFFLINE),
    ]

    def __init__(self, agent_id: str) -> None:
        if not agent_id.strip():
            raise ValueError("agent_id cannot be empty")
        self.agent_id = agent_id
        self.state = AgentState.OFFLINE
        self.history: list[dict[str, Any]] = []
        self._current_call_id: str | None = None

    def can_trigger(self, event: AgentEvent) -> bool:
        """Return whether an event is structurally valid in the current state."""
        return any(t.from_state == self.state and t.event == event for t in self.TRANSITIONS)

    def trigger(self, event: AgentEvent, **kwargs: Any) -> AgentState:
        """Validate and atomically record a transition (within this process)."""
        transition = next((t for t in self.TRANSITIONS if t.from_state == self.state and t.event == event), None)
        if transition is None or (transition.guard is not None and not transition.guard(**kwargs)):
            raise InvalidTransitionError(f"{event.name} cannot be applied in {self.state.name}")
        if event == AgentEvent.CALL_RECEIVED:
            if not isinstance(kwargs.get("call_id"), str) or not kwargs["call_id"].strip():
                raise InvalidTransitionError("CALL_RECEIVED requires a nonempty call_id")
        before = self.state
        if transition.on_enter is not None:
            transition.on_enter(**kwargs)
        if event == AgentEvent.CALL_RECEIVED:
            self._current_call_id = kwargs["call_id"]
        elif event in (AgentEvent.CALL_REJECTED, AgentEvent.CALL_ENDED):
            self._current_call_id = None
        self.state = transition.to_state
        self.history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(), "agent_id": self.agent_id,
            "from_state": before.name, "event": event.name, "to_state": self.state.name,
            "metadata": dict(kwargs),
        })
        return self.state

    def get_history(self) -> list[dict[str, Any]]:
        """Return independent copies of chronological audit entries."""
        return [{**item, "metadata": item["metadata"].copy()} for item in self.history]
