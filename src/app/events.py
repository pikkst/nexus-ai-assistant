"""Runtime events emitted by the Nexus application pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RuntimeState(Enum):
    """Observable high-level application states."""

    STOPPED = "stopped"
    IDLE = "idle"
    LISTENING = "listening"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    ACTING = "acting"
    VERIFYING = "verifying"
    SPEAKING = "speaking"
    WAITING_CONFIRMATION = "waiting_confirmation"
    BLOCKED = "blocked"
    ERROR = "error"
    SLEEPING = "sleeping"


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    """One state transition or pipeline notification."""

    state: RuntimeState
    previous_state: RuntimeState
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
