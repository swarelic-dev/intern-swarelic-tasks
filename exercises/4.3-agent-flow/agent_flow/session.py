"""
agent_flow/session.py — Exercise 4.3

AgentSession wraps AgentStateMachine and tracks timing/performance metrics.
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

    def _accrue_time(self, old_state: AgentState) -> None:
        """Accumulate time spent in old_state before a transition."""
        now = datetime.now()
        elapsed = (now - self._last_state_change).total_seconds()
        self._last_state_change = now

        if old_state == AgentState.ON_CALL:
            self._total_call_time_secs += elapsed
        elif old_state == AgentState.WRAPPING_UP:
            self._total_wrap_time_secs += elapsed
        elif old_state == AgentState.AVAILABLE:
            self._available_time_secs += elapsed

    def process_event(self, event: AgentEvent, **kwargs) -> dict:
        """
        Process an event through the state machine.
        Track timing for calls, wrap-up, and availability.

        Returns:
            dict with keys: success (bool), new_state (str), error (str|None)
        """
        old_state = self.machine.state
        try:
            new_state = self.machine.trigger(event, **kwargs)
            self._accrue_time(old_state)

            # Increment calls_handled when a call fully ends (CALL_ENDED transitions to WRAPPING_UP)
            if event == AgentEvent.CALL_ENDED:
                self._calls_handled += 1

            return {'success': True, 'new_state': new_state.name, 'error': None}

        except InvalidTransitionError as e:
            return {'success': False, 'new_state': old_state.name, 'error': str(e)}

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
                'availability_pct': float,  # time AVAILABLE / total online time
            }
        """
        now = datetime.now()
        session_duration = (now - self.session_start).total_seconds()

        # Accrue time in current state without advancing _last_state_change
        current_elapsed = (now - self._last_state_change).total_seconds()
        current_state = self.machine.state

        call_time = self._total_call_time_secs
        wrap_time = self._total_wrap_time_secs
        avail_time = self._available_time_secs

        if current_state == AgentState.ON_CALL:
            call_time += current_elapsed
        elif current_state == AgentState.WRAPPING_UP:
            wrap_time += current_elapsed
        elif current_state == AgentState.AVAILABLE:
            avail_time += current_elapsed

        avg_call = call_time / self._calls_handled if self._calls_handled > 0 else 0.0

        # Availability % = available time / total session (excluding offline time makes sense here)
        avail_pct = (avail_time / session_duration * 100) if session_duration > 0 else 0.0

        return {
            'agent_id': self.machine.agent_id,
            'current_state': current_state.name,
            'session_duration_secs': round(session_duration, 2),
            'calls_handled': self._calls_handled,
            'avg_call_duration_secs': round(avg_call, 2),
            'total_wrap_time_secs': round(wrap_time, 2),
            'availability_pct': round(avail_pct, 2),
        }
