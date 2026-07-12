"""Runtime events emitted by the Nexus application pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuntimeState(Enum):
    """Observable high-level application states."""

    STOPPED = "stopped"
    IDLE = "idle"
    LISTENING = "listening"
    UNDERSTANDING = "understanding"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    """One state transition or pipeline notification."""

    state: RuntimeState
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
