"""Map authoritative runtime states to existing Nexus face emotions."""

from __future__ import annotations

from .events import RuntimeState

_FACE_EMOTIONS: dict[RuntimeState, str] = {
    RuntimeState.STOPPED: "sleeping",
    RuntimeState.IDLE: "idle",
    RuntimeState.LISTENING: "listening",
    RuntimeState.UNDERSTANDING: "thinking",
    RuntimeState.PLANNING: "thinking",
    RuntimeState.ACTING: "thinking",
    RuntimeState.VERIFYING: "thinking",
    RuntimeState.SPEAKING: "speaking",
    RuntimeState.WAITING_CONFIRMATION: "confused",
    RuntimeState.BLOCKED: "sad",
    RuntimeState.ERROR: "sad",
    RuntimeState.SLEEPING: "sleeping",
}


def face_emotion_for(state: RuntimeState) -> str:
    """Return an emotion value accepted by ``NexusFace.render``."""
    return _FACE_EMOTIONS[state]
