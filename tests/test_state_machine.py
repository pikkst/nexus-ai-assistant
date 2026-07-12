"""Tests for authoritative Nexus runtime state transitions."""

from __future__ import annotations

import pytest

from src.app import (
    InvalidStateTransition,
    RuntimeState,
    RuntimeStateMachine,
    face_emotion_for,
)
from src.ui.face import NexusFace


def test_normal_workflow_emits_typed_transitions() -> None:
    machine = RuntimeStateMachine()
    events = []
    machine.subscribe(events.append)

    machine.transition(RuntimeState.IDLE, "ready")
    machine.transition(RuntimeState.LISTENING)
    machine.transition(RuntimeState.UNDERSTANDING)
    machine.transition(RuntimeState.PLANNING)
    machine.transition(RuntimeState.ACTING)
    machine.transition(RuntimeState.VERIFYING)
    machine.transition(RuntimeState.SPEAKING)
    machine.transition(RuntimeState.IDLE)

    assert events[0].previous_state is RuntimeState.STOPPED
    assert events[0].state is RuntimeState.IDLE
    assert events[-1].previous_state is RuntimeState.SPEAKING
    assert events[-1].state is RuntimeState.IDLE
    assert events[0].created_at.tzinfo is not None


def test_invalid_transition_preserves_state_and_emits_nothing() -> None:
    machine = RuntimeStateMachine()
    events = []
    machine.subscribe(events.append)

    with pytest.raises(InvalidStateTransition, match="stopped to speaking"):
        machine.transition(RuntimeState.SPEAKING)

    assert machine.state is RuntimeState.STOPPED
    assert events == []


def test_interrupted_flow_returns_to_idle() -> None:
    machine = RuntimeStateMachine()
    machine.transition(RuntimeState.IDLE)
    machine.transition(RuntimeState.PLANNING)

    event = machine.interrupt("user cancelled")

    assert machine.state is RuntimeState.IDLE
    assert event.previous_state is RuntimeState.PLANNING
    assert event.message == "user cancelled"


def test_blocked_flow_can_resume_planning() -> None:
    machine = RuntimeStateMachine()
    machine.transition(RuntimeState.IDLE)
    machine.transition(RuntimeState.BLOCKED, "permission required")

    machine.transition(RuntimeState.PLANNING, "permission granted")

    assert machine.state is RuntimeState.PLANNING


def test_error_flow_can_recover_or_stop() -> None:
    machine = RuntimeStateMachine()
    machine.transition(RuntimeState.IDLE)
    machine.transition(RuntimeState.ERROR, "backend unavailable")
    machine.transition(RuntimeState.IDLE, "retry")
    machine.transition(RuntimeState.STOPPED)

    assert machine.state is RuntimeState.STOPPED


@pytest.mark.parametrize("state", list(RuntimeState))
def test_every_state_has_a_face_emotion(state: RuntimeState) -> None:
    emotion = face_emotion_for(state)

    assert emotion in {
        "idle",
        "listening",
        "thinking",
        "speaking",
        "confused",
        "sad",
        "sleeping",
    }
    assert NexusFace().render(emotion).startswith("<svg")


def test_subscriber_failure_does_not_block_other_subscribers() -> None:
    machine = RuntimeStateMachine()
    received = []

    def broken_subscriber(event: object) -> None:
        raise RuntimeError("UI offline")

    machine.subscribe(broken_subscriber)
    machine.subscribe(received.append)

    machine.transition(RuntimeState.IDLE)

    assert len(received) == 1
