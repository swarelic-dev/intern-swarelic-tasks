"""
agent_flow/session.py — Agent Session and Metrics Tracking for Exercise 4.3
"""
from datetime import datetime
from .state_machine import AgentStateMachine, AgentState, AgentEvent, InvalidTransitionError


class AgentSession:
    """Wraps AgentStateMachine and tracks timing/performance metrics."""

    def __init__(self, agent_id: str):
        self.machine = AgentStateMachine(agent_id)
        self.session_start = datetime.now()
        self._calls_handled = 0
        self._total_call_time_secs = 0.0
        self._total_wrap_time_secs = 0.0
        self._available_time_secs = 0.0
        self._last_state_change = self.session_start

    def process_event(self, event: AgentEvent, **kwargs) -> dict:
        """
        Process an event through the state machine.
        Track timing for calls, wrap-up, and availability.

        Returns:
            dict with keys: success (bool), new_state (str), error (str|None)
        """
        now = datetime.now()
        elapsed = (now - self._last_state_change).total_seconds()

        # Update cumulative state durations before transition
        if self.machine.state == AgentState.AVAILABLE:
            self._available_time_secs += elapsed
        elif self.machine.state == AgentState.ON_CALL:
            self._total_call_time_secs += elapsed
        elif self.machine.state == AgentState.WRAPPING_UP:
            self._total_wrap_time_secs += elapsed

        try:
            new_state = self.machine.trigger(event, **kwargs)
            self._last_state_change = now

            if event == AgentEvent.CALL_ENDED:
                self._calls_handled += 1

            return {
                "success": True,
                "new_state": new_state.name,
                "error": None
            }
        except InvalidTransitionError as e:
            return {
                "success": False,
                "new_state": self.machine.state.name,
                "error": str(e)
            }

    def get_metrics(self) -> dict:
        """
        Return session performance metrics.

        Returns:
            {
                'agent_id': str,
                'current_state': str,
                'session_duration_secs': float,
                'calls_handled': int,
                'avg_call_duration_secs': float,
                'total_wrap_time_secs': float,
                'availability_pct': float,  # time AVAILABLE / total session time
            }
        """
        now = datetime.now()
        elapsed = (now - self._last_state_change).total_seconds()

        current_avail = self._available_time_secs + (
            elapsed if self.machine.state == AgentState.AVAILABLE else 0.0
        )
        current_call_time = self._total_call_time_secs + (
            elapsed if self.machine.state == AgentState.ON_CALL else 0.0
        )
        current_wrap_time = self._total_wrap_time_secs + (
            elapsed if self.machine.state == AgentState.WRAPPING_UP else 0.0
        )

        session_duration = max(0.0001, (now - self.session_start).total_seconds())

        avg_call_duration = (
            (current_call_time / self._calls_handled) if self._calls_handled > 0 else 0.0
        )

        availability_pct = min(100.0, max(0.0, (current_avail / session_duration) * 100.0))

        return {
            'agent_id': self.machine.agent_id,
            'current_state': self.machine.state.name,
            'session_duration_secs': session_duration,
            'calls_handled': self._calls_handled,
            'avg_call_duration_secs': avg_call_duration,
            'total_wrap_time_secs': current_wrap_time,
            'availability_pct': availability_pct,
        }
