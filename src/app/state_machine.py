"""Validated authoritative state machine for the Nexus runtime."""

from __future__ import annotations

import logging
from collections.abc import Callable

from .events import RuntimeEvent, RuntimeState

logger = logging.getLogger(__name__)


class InvalidStateTransition(RuntimeError):
    """Raised when a requested runtime transition is not allowed."""


_ACTIVE_STATES = set(RuntimeState) - {RuntimeState.STOPPED}
_TRANSITIONS: dict[RuntimeState, set[RuntimeState]] = {
    RuntimeState.STOPPED: {RuntimeState.IDLE},
    RuntimeState.IDLE: {
        RuntimeState.LISTENING,
        RuntimeState.UNDERSTANDING,
        RuntimeState.PLANNING,
        RuntimeState.WAITING_CONFIRMATION,
        RuntimeState.BLOCKED,
        RuntimeState.SLEEPING,
        RuntimeState.ERROR,
        RuntimeState.STOPPED,
    },
    RuntimeState.LISTENING: {
        RuntimeState.UNDERSTANDING,
        RuntimeState.IDLE,
        RuntimeState.ERROR,
        RuntimeState.STOPPED,
    },
    RuntimeState.UNDERSTANDING: {
        RuntimeState.PLANNING,
        RuntimeState.BLOCKED,
        RuntimeState.ERROR,
        RuntimeState.STOPPED,
    },
    RuntimeState.PLANNING: {
        RuntimeState.ACTING,
        RuntimeState.VERIFYING,
        RuntimeState.WAITING_CONFIRMATION,
        RuntimeState.BLOCKED,
        RuntimeState.IDLE,
        RuntimeState.ERROR,
        RuntimeState.STOPPED,
    },
    RuntimeState.ACTING: {
        RuntimeState.VERIFYING,
        RuntimeState.WAITING_CONFIRMATION,
        RuntimeState.BLOCKED,
        RuntimeState.ERROR,
        RuntimeState.STOPPED,
    },
    RuntimeState.VERIFYING: {
        RuntimeState.SPEAKING,
        RuntimeState.IDLE,
        RuntimeState.BLOCKED,
        RuntimeState.ERROR,
        RuntimeState.STOPPED,
    },
    RuntimeState.SPEAKING: {
        RuntimeState.IDLE,
        RuntimeState.LISTENING,
        RuntimeState.ERROR,
        RuntimeState.STOPPED,
    },
    RuntimeState.WAITING_CONFIRMATION: {
        RuntimeState.PLANNING,
        RuntimeState.ACTING,
        RuntimeState.IDLE,
        RuntimeState.ERROR,
        RuntimeState.STOPPED,
    },
    RuntimeState.BLOCKED: {
        RuntimeState.PLANNING,
        RuntimeState.IDLE,
        RuntimeState.ERROR,
        RuntimeState.STOPPED,
    },
    RuntimeState.ERROR: {
        RuntimeState.IDLE,
        RuntimeState.PLANNING,
        RuntimeState.STOPPED,
    },
    RuntimeState.SLEEPING: {RuntimeState.IDLE, RuntimeState.STOPPED},
}


class RuntimeStateMachine:
    """Own runtime state and publish only validated transitions."""

    def __init__(self) -> None:
        self._state = RuntimeState.STOPPED
        self._subscribers: list[Callable[[RuntimeEvent], None]] = []

    @property
    def state(self) -> RuntimeState:
        return self._state

    def subscribe(self, callback: Callable[[RuntimeEvent], None]) -> None:
        self._subscribers.append(callback)

    def can_transition(self, target: RuntimeState) -> bool:
        return target == self._state or target in _TRANSITIONS[self._state]

    def transition(
        self,
        target: RuntimeState,
        message: str = "",
        data: dict[str, object] | None = None,
    ) -> RuntimeEvent:
        """Move to target and notify subscribers, or fail without mutation."""
        previous = self._state
        if not self.can_transition(target):
            raise InvalidStateTransition(f"Cannot transition from {previous.value} to {target.value}")
        self._state = target
        event = RuntimeEvent(
            state=target,
            previous_state=previous,
            message=message,
            data=dict(data or {}),
        )
        for subscriber in tuple(self._subscribers):
            try:
                subscriber(event)
            except Exception:
                logger.exception("Runtime state subscriber failed")
        return event

    def interrupt(self, message: str = "Interrupted") -> RuntimeEvent:
        """Return any running state to idle without special caller logic."""
        if self._state not in _ACTIVE_STATES:
            raise InvalidStateTransition("Cannot interrupt a stopped runtime")
        if RuntimeState.IDLE not in _TRANSITIONS[self._state] and self._state != RuntimeState.IDLE:
            raise InvalidStateTransition(f"Cannot interrupt state {self._state.value}")
        return self.transition(RuntimeState.IDLE, message)
