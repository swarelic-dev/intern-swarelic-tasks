"""Per-session utilization and handling-time metrics."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .state_machine import AgentEvent, AgentState, AgentStateMachine


class AgentSession:
    """Track time spent in states and successful completed calls."""

    def __init__(self, agent_id: str) -> None:
        self.machine = AgentStateMachine(agent_id)
        self.session_start = datetime.now(timezone.utc)
        self._state_entered = self.session_start
        self._online_since: datetime | None = None
        self._available_secs = 0.0
        self._online_secs = 0.0
        self._calls_handled = 0
        self._total_call_time_secs = 0.0
        self._total_wrap_time_secs = 0.0

    def process_event(self, event: AgentEvent, **kwargs: Any) -> dict[str, Any]:
        """Apply a valid event and account for time in the previous state."""
        previous = self.machine.state
        new_state = self.machine.trigger(event, **kwargs)
        now = datetime.now(timezone.utc)
        elapsed = max(0.0, (now - self._state_entered).total_seconds())
        if previous == AgentState.AVAILABLE:
            self._available_secs += elapsed
        if previous == AgentState.ON_CALL:
            self._total_call_time_secs += elapsed
        if previous == AgentState.WRAPPING_UP:
            self._total_wrap_time_secs += elapsed
        if previous != AgentState.OFFLINE:
            self._online_secs += elapsed
        if event == AgentEvent.CALL_ENDED:
            self._calls_handled += 1
        self._state_entered = now
        return {"agent_id": self.machine.agent_id, "state": new_state.name, "event": event.name}

    def get_metrics(self) -> dict[str, float | int | str]:
        """Calculate live elapsed session, call, and utilization statistics."""
        now = datetime.now(timezone.utc)
        elapsed = max(0.0, (now - self._state_entered).total_seconds())
        online = self._online_secs + (elapsed if self.machine.state != AgentState.OFFLINE else 0)
        available = self._available_secs + (elapsed if self.machine.state == AgentState.AVAILABLE else 0)
        call_time = self._total_call_time_secs + (elapsed if self.machine.state == AgentState.ON_CALL else 0)
        return {
            "session_duration_secs": max(0.0, (now - self.session_start).total_seconds()),
            "calls_handled": self._calls_handled,
            "avg_call_duration_secs": call_time / self._calls_handled if self._calls_handled else 0.0,
            "availability_pct": 100 * available / online if online else 0.0,
            "current_state": self.machine.state.name,
        }
